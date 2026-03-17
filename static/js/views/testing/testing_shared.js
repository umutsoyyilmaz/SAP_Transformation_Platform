/**
 * SAP Transformation Management Platform
 * Testing Shared — common state & utilities for Test Planning, Execution,
 * and Defect Management modules.
 */

const TestingShared = (() => {
    let selectedProgramId = null;
    const TESTING_OPERATIONAL_PERMISSION_SOURCE = 'testingOperational';
    const OPERATIONAL_PERMISSION_ACTIONS = [
        'approval_configure',
        'approval_submit',
        'approval_decide',
        'signoff_manage',
        'retest_manage',
        'release_decide',
    ];
    const moduleOrder = [
        { id: 'test-overview', label: 'Overview', sublabel: 'Readiness, role cockpit, and focus queue', icon: '◌' },
        { id: 'test-planning', label: 'Plans & Cases', sublabel: 'Catalog, suites, and test plan setup', icon: '☰' },
        { id: 'execution-center', label: 'Execution Center', sublabel: 'Queue, failures, blockers, and traceability', icon: '▶' },
        { id: 'defects-retest', label: 'Defects & Retest', sublabel: 'Defect triage, SLA risk, and retest chain', icon: '!' },
        { id: 'signoff-approvals', label: 'Approvals & Sign-off', sublabel: 'Pending approvals and final decision flow', icon: '✓' },
    ];

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    function getProgram() {
        const prog = App.getActiveProgram();
        selectedProgramId = prog ? prog.id : null;
        return selectedProgramId;
    }

    function _registerOperationalPermissionSource() {
        if (typeof RoleNav === 'undefined' || typeof RoleNav.registerPermissionSource !== 'function') {
            return;
        }
        const existing = RoleNav.getPermissionSnapshot(TESTING_OPERATIONAL_PERMISSION_SOURCE);
        if (existing !== null) {
            return;
        }
        try {
            RoleNav.registerPermissionSource(TESTING_OPERATIONAL_PERMISSION_SOURCE, {
                fetcher: async (programId) => {
                    const payload = await API.get(`/programs/${programId}/testing/operational-permissions`);
                    return {
                        roles: payload.current_roles || [],
                        permissions: new Set(
                            Object.entries(payload.permissions || {})
                                .filter(([, meta]) => Boolean(meta?.allowed))
                                .map(([action]) => action),
                        ),
                        raw: payload,
                    };
                },
            });
        } catch (_error) {
            // Source already registered in the current runtime.
        }
    }

    function getProject() {
        const project = App.getActiveProject();
        return project ? project.id : null;
    }

    function noProgramHtml(title) {
        return PGEmptyState.html({ icon: 'test', title: title || 'No Program Selected', description: 'Select a program to continue.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
    }

    function renderModuleNav(activeView) {
        return `<div class="workspace-nav" data-testid="test-hub-nav" style="margin:12px 0 20px">
            ${moduleOrder.map((item) => `
                <button
                    type="button"
                    class="workspace-nav__item${item.id === activeView ? ' workspace-nav__item--active' : ''}"
                    data-testing-view="${item.id}"
                    ${item.id === activeView ? 'aria-current="page"' : ''}
                    onclick="App.navigate('${item.id}')"
                >
                    <span class="workspace-nav__icon" aria-hidden="true">${item.icon}</span>
                    <span class="workspace-nav__body">
                        <span class="workspace-nav__label">${esc(item.label)}</span>
                        <span class="workspace-nav__sub">${esc(item.sublabel)}</span>
                    </span>
                </button>
            `).join('')}
        </div>`;
    }

    function getRoleContext() {
        const roles = getUserRoles();

        const roleText = roles.join(' ');
        if (roleText.includes('business') || roleText.includes('uat_tester') || roleText.includes('tester')) {
            return {
                mode: 'business',
                title: 'Business Tester Workspace',
                subtitle: 'Keep execution steps, evidence capture, and blocked scenarios visible without exposing planning-heavy setup.',
                route: 'business-tester-workspace',
            };
        }
        if (roleText.includes('lead') || roleText.includes('uat') || roleText.includes('sit')) {
            return {
                mode: 'lead',
                title: 'SIT / UAT Lead Cockpit',
                subtitle: 'Watch blockers, retest pressure, and sign-off readiness across the active testing scope.',
                route: 'test-lead-cockpit',
            };
        }
        return {
            mode: 'manager',
            title: 'Test Manager Cockpit',
            subtitle: 'Drive execution capacity, triage risk, and sign-off readiness from one operations-first control point.',
            route: 'test-manager-cockpit',
        };
    }

    function getUserRoles() {
        const roleUser = (typeof RoleNav !== 'undefined' && RoleNav.getUser) ? RoleNav.getUser() : null;
        const authUser = (typeof Auth !== 'undefined' && Auth.getUser) ? Auth.getUser() : null;
        return []
            .concat(Array.isArray(authUser?.roles) ? authUser.roles : [])
            .concat(roleUser?.default_role ? [roleUser.default_role] : [])
            .map((role) => String(role || '').toLowerCase())
            .filter(Boolean);
    }

    async function ensureOperationalPermissions(forceRefresh = false) {
        _registerOperationalPermissionSource();
        if (typeof RoleNav === 'undefined' || typeof RoleNav.preloadSource !== 'function') {
            return null;
        }
        const payload = await RoleNav.preloadSource(TESTING_OPERATIONAL_PERMISSION_SOURCE, { forceRefresh });
        return payload?.raw || null;
    }

    function getOperationalPermissions() {
        _registerOperationalPermissionSource();
        if (typeof RoleNav === 'undefined' || typeof RoleNav.getPermissionSnapshot !== 'function') {
            return null;
        }
        return RoleNav.getPermissionSnapshot(TESTING_OPERATIONAL_PERMISSION_SOURCE)?.raw || null;
    }

    function canPerform(action) {
        const roles = getUserRoles();
        if (!roles.length) return true;
        if (roles.includes('platform_admin') || roles.includes('tenant_admin') || roles.includes('admin')) return true;

        _registerOperationalPermissionSource();
        if (typeof RoleNav === 'undefined' || typeof RoleNav.canSyncInSource !== 'function') {
            return false;
        }
        return RoleNav.canSyncInSource(TESTING_OPERATIONAL_PERMISSION_SOURCE, action);
    }

    function resetOperationalPermissions() {
        if (typeof RoleNav !== 'undefined' && typeof RoleNav.resetCache === 'function') {
            RoleNav.resetCache();
        }
    }

    return {
        esc,
        getProgram,
        getProject,
        noProgramHtml,
        getRoleContext,
        getUserRoles,
        ensureOperationalPermissions,
        getOperationalPermissions,
        canPerform,
        resetOperationalPermissions,
        renderModuleNav,
        OPERATIONAL_PERMISSION_ACTIONS,
        get pid() { return getProgram(); },
        get projectId() { return getProject(); },
    };
})();
