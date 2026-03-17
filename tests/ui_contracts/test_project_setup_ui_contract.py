"""Frontend/backend contract checks for the Project Setup bootstrap cockpit."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT_SETUP_JS = ROOT / "static/js/views/setup/project_setup.js"
PROJECT_SETUP_SHELL_JS = ROOT / "static/js/views/setup/project_setup_shell.js"
EXPLORE_API_JS = ROOT / "static/js/explore-api.js"
PROJECT_SERVICE_PY = ROOT / "app/services/project_service.py"
INDEX_HTML = ROOT / "templates/index.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_project_setup_exposes_project_owned_governance_and_team_workstream_binding():
    src = _read(PROJECT_SETUP_JS)
    shell_src = _read(PROJECT_SETUP_SHELL_JS)

    assert "data-setup-tab=\"${tab.id}\"" in shell_src
    assert "id: 'workstreams'" in shell_src
    assert "id: 'committees'" in shell_src
    assert "id=\"tm_workstream_id\"" in src
    assert "workstream_id: document.getElementById('tm_workstream_id')?.value" in src
    assert "API.get(`/programs/${_pid}/workstreams?project_id=${_activeProject.id}`)" in src
    assert "API.post(`/programs/${_pid}/workstreams`, payload)" in src
    assert "API.post(`/programs/${_pid}/committees`, payload)" in src
    assert "TeamMemberPicker.invalidateCache(_pid)" in src
    assert "ProjectSetupView._openWorkstreamForm(null)" in src
    assert "ProjectSetupView._openCommitteeForm(null)" in src
    assert "renderWorkstreamsTab" in src
    assert "renderCommitteesTab" in src
    assert "data-testid=\"project-setup-confirm-modal\"" in src
    assert "data-testid=\"project-setup-confirm-submit\"" in src
    assert "data-testid=\"project-setup-confirm-cancel\"" in src
    assert "confirm(" not in src


def test_project_setup_moves_methodology_edit_out_of_project_info():
    src = _read(PROJECT_SETUP_JS)
    info_src = _read(ROOT / "static/js/views/setup/project_setup_info.js")
    shell_src = _read(PROJECT_SETUP_SHELL_JS)

    assert "Open Methodology" in info_src
    assert "ProjectSetupView.switchTab('methodology')" in info_src
    assert "id=\"pi_methodology\"" not in info_src
    assert "id=\"pi_project_type\"" not in info_src
    assert "id=\"pi_sap_product\"" not in info_src
    assert "id=\"pi_deployment_option\"" not in info_src
    assert "_shell().renderTabs(_currentTab)" in src
    assert "renderProfileStrip" in shell_src


def test_project_setup_hierarchy_uses_active_project_scope():
    setup_src = _read(PROJECT_SETUP_JS)
    api_src = _read(EXPLORE_API_JS)

    assert "ExploreAPI.levels.listTree(_activeProject.id, { max_depth: 2 })" in setup_src
    assert "ExploreAPI.levels.listL1(_activeProject.id)" not in setup_src
    assert "ExploreAPI.levels.listL2(_activeProject.id)" not in setup_src
    assert "ExploreAPI.levels.listL3(_activeProject.id)" not in setup_src
    assert "ExploreAPI.levels.listL4(_activeProject.id)" not in setup_src
    assert "ExploreAPI.levels.listChildren(_activeProject.id, id)" in setup_src
    assert "mutation_context: HIERARCHY_MUTATION_CONTEXT" in setup_src
    assert "ExploreAPI.levels.bulkCreate(_activeProject.id, rows, {" in setup_src
    assert "ExploreAPI.levels.importTemplate(_activeProject.id" in setup_src
    assert "listTree: (projectId, params)" in api_src
    assert "listChildren: (projectId, parentId, params)" in api_src
    assert "process-levels?project_id=${projectId}&level=1" in api_src
    assert "Object.assign({project_id: projectId}, data)" in api_src
    assert "process-levels/import-template`, Object.assign({project_id: projectId}, data)" in api_src
    assert "params.set('mutation_context', data.mutation_context)" in api_src
    assert "Project Setup owns the baseline structure" in setup_src
    assert "HierarchyUI.bridgeCard({" in setup_src
    assert "HierarchyWidgets.filterToolbar({" in setup_src
    assert "HierarchyWidgets.treeShell({" in setup_src
    assert "HierarchyWidgets.choiceGrid({" in setup_src
    assert "HierarchyWidgets.modalFrame({" in setup_src
    assert "HierarchyRenderers.treeRow({" in setup_src
    assert "HierarchyRenderers.tableCard({" in setup_src
    assert "HierarchyRenderers.tableRow({" in setup_src
    assert "function _currentHierarchyQuery()" in setup_src
    assert "function _scheduleHierarchyReload()" in setup_src
    assert "HierarchyUI.loading({ label: 'Loading project baseline…' })" in setup_src
    assert "/static/js/components/hierarchy/hierarchy-shared.js" in _read(INDEX_HTML)
    assert "/static/js/components/hierarchy/hierarchy-widgets.js" in _read(INDEX_HTML)
    assert "/static/js/components/hierarchy/hierarchy-renderers.js" in _read(INDEX_HTML)
    assert "ProjectSetupView.openExecutionScope()" in setup_src
    assert "ProjectSetupView.openWorkshopHub()" in setup_src


def test_project_service_applies_operational_fields():
    src = _read(PROJECT_SERVICE_PY)

    assert "_apply_operational_fields(project, data)" in src
    assert "wave_number" in src
    assert "sap_product" in src
    assert "project_type" in src
    assert "methodology" in src
    assert "deployment_option" in src
    assert "priority" in src
    assert "project_rag" in src
