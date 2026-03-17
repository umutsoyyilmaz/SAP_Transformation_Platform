"""Contract checks for Test Management IA refresh."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static/js/app.js"
INDEX_HTML = ROOT / "templates/index.html"
OVERVIEW_JS = ROOT / "static/js/views/testing/test_overview.js"
SHARED_JS = ROOT / "static/js/views/testing/testing_shared.js"
EXECUTION_JS = ROOT / "static/js/views/testing/test_execution.js"
DEFECT_JS = ROOT / "static/js/views/testing/defect_management.js"
DETAIL_JS = ROOT / "static/js/views/testing/test_case_detail.js"
PLANNING_JS = ROOT / "static/js/views/testing/test_planning.js"
PLAN_DETAIL_JS = ROOT / "static/js/views/testing/test_plan_detail.js"
EVIDENCE_JS = ROOT / "static/js/views/testing/evidence_capture.js"
APPROVALS_JS = ROOT / "static/js/views/governance/approvals.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_router_registers_operations_first_test_management_routes():
    src = _read(APP_JS)
    assert "'test-overview': () => TestOverviewView.render()" in src
    assert "'test-manager-cockpit': () => TestOverviewView.render('manager')" in src
    assert "'test-lead-cockpit': () => TestOverviewView.render('lead')" in src
    assert "'business-tester-workspace': () => TestOverviewView.render('business')" in src
    assert "'execution-center': () => TestExecutionView.render()" in src
    assert "'defects-retest': () => DefectManagementView.render()" in src
    assert "'signoff-approvals': () => ApprovalsView.render()" in src
    assert "function _resolveHashRoute()" in src
    assert "test-case-detail" in src
    assert "if (!_navigateFromHashIfPossible()) {" in src


def test_sidebar_uses_new_test_management_labels():
    src = _read(INDEX_HTML)
    assert 'data-view="test-overview"' in src
    assert 'Test</span>' in src
    assert 'data-view="test-planning"' not in src
    assert 'data-view="execution-center"' not in src
    assert 'data-view="defects-retest"' not in src
    assert 'data-view="signoff-approvals"' not in src


def test_testing_shared_exposes_cross_module_navigation():
    src = _read(SHARED_JS)
    assert "function renderModuleNav(activeView)" in src
    assert "function getRoleContext()" in src
    assert "function getProject()" in src
    assert "function getUserRoles()" in src
    assert "async function ensureOperationalPermissions(forceRefresh = false)" in src
    assert "function getOperationalPermissions()" in src
    assert "function canPerform(action)" in src
    assert "get pid() { return getProgram(); }" in src
    assert "get projectId() { return getProject(); }" in src
    assert 'data-testid="test-hub-nav"' in src
    assert "workspace-nav__item" in src
    assert "test-manager-cockpit" in src
    assert "test-lead-cockpit" in src
    assert "business-tester-workspace" in src
    assert "test-overview" in src
    assert "execution-center" in src
    assert "defects-retest" in src
    assert "signoff-approvals" in src
    assert "approval_configure" in src
    assert "approval_submit" in src
    assert "approval_decide" in src
    assert "signoff_manage" in src
    assert "retest_manage" in src
    assert "release_decide" in src
    assert "/testing/operational-permissions" in src


def test_test_overview_acts_as_operations_first_landing():
    src = _read(OVERVIEW_JS)
    assert 'data-testid="test-overview-page"' in src
    assert 'data-testid="release-readiness-panel"' in src
    assert 'data-testid="role-workspace-page"' in src
    assert 'data-testid="role-workspace-grid"' in src
    assert 'data-testid="role-workspace-checklist"' in src
    assert 'data-testid="manager-risk-board"' in src
    assert 'data-testid="lead-ops-board"' in src
    assert 'data-testid="business-approval-board"' in src
    assert 'data-testid="role-workspace-actions"' in src
    assert 'Operations-first landing' in src
    assert "TestingShared.getRoleContext()" in src
    assert 'Role-Based Cockpit' in src
    assert 'Business Tester Workspace' in src
    assert 'SIT / UAT Lead Cockpit' in src
    assert 'Test Manager Cockpit' in src
    assert 'data-testid="role-cockpit-panel"' in src
    assert "Open Workspace" in src
    assert "route: 'execution-center'" in src
    assert "route: 'defects-retest'" in src
    assert "route: 'signoff-approvals'" in src
    assert "/testing/overview-summary" in src
    assert "/testing/dashboard/cycle-risk" not in src
    assert "/testing/dashboard/retest-readiness" not in src
    assert "/programs/${_pid}/testing/catalog" not in src
    assert "/programs/${_pid}/testing/plans" not in src
    assert "/programs/${_pid}/testing/defects" not in src
    assert "/approvals/pending?program_id=${_pid}" not in src
    assert "renderManagerRiskBoard" in src
    assert "renderLeadOpsBoard" in src
    assert "renderBusinessApprovalBoard" in src
    assert "renderReleaseReadinessChain" in src
    assert "Release Readiness Chain" in src


def test_execution_center_exposes_queue_first_tabs_and_ops_shell():
    src = _read(EXECUTION_JS)
    assert "let currentTab = 'queue';" in src
    assert "switchTab('queue')" in src
    assert "switchTab('failed')" in src
    assert "switchTab('blocked')" in src
    assert "switchTab('retest')" in src
    assert 'data-testid="execution-center-ops"' in src
    assert "reportExecutionDefect" in src
    assert "openExecutionEvidence" in src
    assert "openQuickRunCycle,\n        openExecutionEvidence," in src
    assert "openExecutionCase" in src
    assert "related_pending_approvals" in src
    assert "/testing/execution-center" in src
    assert "/testing/dashboard/cycle-risk" not in src
    assert "/testing/dashboard/retest-readiness" not in src
    assert "_retestReadinessCache" in src
    assert "_releaseReadinessCache" in src
    assert "_mergedRetestRows" in src
    assert "Retest Readiness" in src
    assert 'data-testid="release-readiness-board"' in src
    assert "Release Readiness" in src
    assert "cycleTransportRequest" in src
    assert "cycleDeploymentBatch" in src
    assert "cycleReleaseTrain" in src
    assert "cycleOwner" in src
    assert "signoff_manage" in src
    assert "Open defects: " in src
    assert "execution_id: execution.id || execId" in src
    assert "Cycle Sign-off Risk & Approval Readiness" in src
    assert "_renderCycleRiskDashboard" in src
    assert "'execution-confirm-modal'" in src
    assert "'execution-confirm-submit'" in src
    assert "'execution-confirm-cancel'" in src
    assert "deletePlanConfirmed" in src
    assert "deleteCycleConfirmed" in src
    assert "deleteExecConfirmed" in src
    assert "deleteSignoffConfirmed" in src
    assert "deleteRunConfirmed" in src
    assert "confirm(" not in src


def test_defect_management_surfaces_retest_and_approval_chain():
    src = _read(DEFECT_JS)
    assert "Defect → Retest → Approval Chain" in src
    assert "defectApprovalBanner" in src
    assert "ApprovalsView.renderStatusBanner" in src
    assert "openExecutionChain" in src
    assert "openExecStepExecution" in src
    assert "viewCycleExecs" in src


def test_test_case_detail_rehydrates_program_context_for_deep_links():
    src = _read(DETAIL_JS)
    assert "const pid = TestingShared.getProgram();" in src
    assert "await _loadData(TestingShared.getProgram(), _caseId);" in src
    assert "/testing/catalog/${_caseId}/execution-history" in src
    assert "/testing/plans/${p.id}" not in src


def test_traceability_pickes_use_project_context():
    planning_src = _read(PLANNING_JS)
    plan_detail_src = _read(PLAN_DETAIL_JS)
    assert "const projectId = TestingShared.getProject();" in planning_src
    assert "project_id=${projectId}" in planning_src
    assert "Select an active project to load L3 process levels." in planning_src
    assert "const projectId = TestingShared.getProject();" in plan_detail_src
    assert "project_id=${projectId}" in plan_detail_src
    assert "Select an active project to load Explore scope items." in plan_detail_src
    assert "/testing/release-readiness" in plan_detail_src
    assert "Build / Transport" in plan_detail_src
    assert "Owner" in plan_detail_src
    assert "Readiness" in plan_detail_src


def test_approvals_view_honours_operational_roles():
    src = _read(APPROVALS_JS)
    assert "TestingShared.canPerform('approval_decide')" in src
    assert "TestingShared.canPerform('approval_submit')" in src
    assert "await TestingShared.ensureOperationalPermissions();" in src
    assert "Operational submit role required" in src
    assert "Role required" in src


def test_evidence_capture_uses_spa_root_and_scoped_api_context():
    src = _read(EVIDENCE_JS)
    assert 'const root = $("#mainContent") || document.body;' in src
    assert "API.get(`/testing/executions/${currentExecutionId}/evidence`)" in src
    assert "API.post(`/evidence/${id}/set-primary`, {})" in src
    assert "API.delete(`/evidence/${id}`)" in src
    assert "fetch(" not in src
