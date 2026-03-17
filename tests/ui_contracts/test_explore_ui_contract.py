"""Contract checks for the Explore IA refresh."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static/js/app.js"
INDEX_HTML = ROOT / "templates/index.html"
OVERVIEW_JS = ROOT / "static/js/views/explore/explore_dashboard.js"
OUTCOMES_JS = ROOT / "static/js/views/explore/explore_outcomes.js"
WORKSHOP_DETAIL_JS = ROOT / "static/js/views/explore/explore_workshop_detail.js"
SHARED_JS = ROOT / "static/js/components/explore/explore-shared.js"
API_JS = ROOT / "static/js/explore-api.js"
HIERARCHY_JS = ROOT / "static/js/views/explore/explore_hierarchy.js"
WORKSHOPS_JS = ROOT / "static/js/views/explore/explore_workshops.js"
WORKSHOP_DETAIL_JS = ROOT / "static/js/views/explore/explore_workshop_detail.js"
REQUIREMENTS_JS = ROOT / "static/js/views/explore/explore_requirements.js"
TIMELINE_JS = ROOT / "static/js/views/portfolio/timeline.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_router_registers_new_explore_information_architecture_views():
    src = _read(APP_JS)
    assert "'explore-overview': () => ExploreDashboardView.render()" in src
    assert "'explore-scope': () => ExploreHierarchyView.render()" in src
    assert "'explore-outcomes': () => ExploreOutcomeHubView.render()" in src
    assert "'explore-traceability': () => ExploreOutcomeHubView.renderForTraceabilityRoute()" in src


def test_sidebar_exposes_new_explore_navigation_labels():
    src = _read(INDEX_HTML)
    assert 'data-view="explore-overview"' in src
    assert 'Explore</span>' in src
    assert 'data-view="explore-scope"' not in src
    assert 'data-view="explore-outcomes"' not in src
    assert 'data-view="explore-traceability"' not in src


def test_overview_and_outcome_views_expose_stage_navigation_and_testids():
    overview_src = _read(OVERVIEW_JS)
    outcomes_src = _read(OUTCOMES_JS)
    shared_src = _read(SHARED_JS)
    assert 'data-testid="explore-overview-page"' in overview_src
    assert 'data-testid="explore-stage-nav"' in shared_src
    assert "App.navigate('explore-outcomes')" in overview_src
    assert "let _pageTestId = 'explore-outcomes-page';" in outcomes_src
    assert "pageTestId: 'explore-traceability-page'" in outcomes_src
    assert "ExpUI.exploreStageNav({ current: 'explore-traceability' })" in outcomes_src


def test_workshop_detail_promotes_outcome_summary_and_direct_entry():
    src = _read(WORKSHOP_DETAIL_JS)
    assert "function renderOutcomeSummary()" in src
    assert "function summary()" in src
    assert "const totals = summary();" in src
    assert "totals.fit_summary" in src
    assert "totals.handed_off_total" in src
    assert "totals.blocked_total" in src
    assert "launchOutcome('decision')" in src
    assert "launchOutcome('openItem')" in src
    assert "launchOutcome('requirement')" in src


def test_explore_execution_views_resolve_scope_from_active_project():
    for path in (OVERVIEW_JS, HIERARCHY_JS, WORKSHOPS_JS, WORKSHOP_DETAIL_JS, OUTCOMES_JS, REQUIREMENTS_JS):
        src = _read(path)
        assert "App.getActiveProject()" in src
        assert "Select a project first" in src

    hierarchy_src = _read(HIERARCHY_JS)
    assert "ExploreAPI.levels.listTree(_pid, { max_depth: 2 })" in hierarchy_src
    assert "ExploreAPI.levels.listChildren(_pid, id)" in hierarchy_src
    assert "ExploreAPI.levels.scopeMatrix(_pid, _currentMatrixQuery())" in hierarchy_src
    assert "function _currentMatrixQuery()" in hierarchy_src
    assert "function setMatrixPage(page)" in hierarchy_src
    assert "Page ${_matrixMeta.page} / ${_matrixMeta.pages}" in hierarchy_src
    assert "ExploreAPI.levels.listL1(_pid)" not in hierarchy_src
    assert "ExploreAPI.levels.listL2(_pid)" not in hierarchy_src
    assert "ExploreAPI.levels.listL3(_pid)" not in hierarchy_src
    assert "ExploreAPI.levels.listL4(_pid)" not in hierarchy_src
    assert "function _currentTreeQuery()" in hierarchy_src
    assert "function _shouldUseLazyTree()" in hierarchy_src
    assert "function _scheduleReload()" in hierarchy_src


def test_scope_process_is_execution_workspace_not_baseline_bootstrap():
    src = _read(HIERARCHY_JS)
    index_src = _read(INDEX_HTML)

    assert "Scope &amp; Process reviews the baseline, it does not redefine it" in src
    assert "Structural baseline changes belong in <strong>Project Setup &gt; Scope &amp; Hierarchy</strong>." in src
    assert "Scope Change Queue" in src
    assert "Open Project Setup" in src
    assert "HierarchyUI.bridgeCard({" in src
    assert "HierarchyUI.emptyState({" in src
    assert "HierarchyUI.loading({ label: 'Loading execution scope…' })" in src
    assert "HierarchyWidgets.filterToolbar({" in src
    assert "HierarchyWidgets.treeShell({" in src
    assert "HierarchyWidgets.detailPanel({" in src
    assert "HierarchyWidgets.modalFrame({" in src
    assert "HierarchyRenderers.treeRow({" in src
    assert "HierarchyRenderers.tableCard({" in src
    assert "HierarchyRenderers.tableRow({" in src
    assert "HierarchyRenderers.detailSection({" in src
    assert "HierarchyRenderers.detailRow({" in src
    assert "/static/js/components/hierarchy/hierarchy-shared.js" in index_src
    assert "/static/js/components/hierarchy/hierarchy-widgets.js" in index_src
    assert "/static/js/components/hierarchy/hierarchy-renderers.js" in index_src
    assert "openSeedingDialog, submitSeedImport," not in src
    assert "openCatalogSeedWizard, _submitCatalogSeed," not in src


def test_explore_api_uses_project_id_for_execution_routes():
    src = _read(API_JS)
    assert "workshops?project_id=" in src
    assert "requirements?project_id=" in src
    assert "open-items?project_id=" in src
    assert "scope-change-requests?project_id=" in src
    assert "attachments?project_id=" in src
    assert "snapshots?project_id=" in src
    assert "reports/steering-committee?project_id=" in src
    assert "scope-matrix?project_id=${projectId}${_qs(params)}" in src


def test_workshop_hub_consumes_server_side_stats_and_readiness_payloads():
    src = _read(WORKSHOPS_JS)
    assert "ExploreAPI.workshops.stats(_pid)" in src
    assert "ExploreAPI.levels.areaMilestones(_pid)" in src
    assert "async function ensureL3Items()" in src
    assert "const filterOptions = _stats.filter_options || {};" in src
    assert "const items = _areaMilestones || [];" in src
    assert "steps_total" not in src.split("function renderKpiStrip()", 1)[1].split("function renderFilterBar()", 1)[0]


def test_timeline_view_exposes_program_milestone_crud_actions():
    src = _read(TIMELINE_JS)
    assert "TimelineView.openMilestoneModal()" in src
    assert "function openMilestoneModal(recordId = null)" in src
    assert "function submitMilestoneForm(event, recordId = null)" in src
    assert "function deleteMilestone(recordId)" in src
    assert "function setMilestoneFilter(key, value)" in src
    assert "_milestoneFilterToolbar" in src
    assert "Search title, code, owner" in src
    assert "API.post(`/programs/${_programId}/milestones`, payload)" in src
    assert "API.put(`/program-milestones/${recordId}`, payload)" in src
    assert "API.delete(`/program-milestones/${recordId}`)" in src
    assert 'RoleNav.preloadSource(PLATFORM_PERMISSION_SOURCE)' in src
    assert 'RoleNav.canSyncInSource(PLATFORM_PERMISSION_SOURCE, "programs.edit")' in src
    assert 'RoleNav.canSyncInSource(PLATFORM_PERMISSION_SOURCE, "programs.delete")' in src
