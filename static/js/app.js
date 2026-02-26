/**
 * SAP Transformation Management Platform
 * SPA Router — Handles sidebar navigation and view rendering.
 */

const App = (() => {
    // ── Utility ──────────────────────────────────────────────────────────
    function esc(str) {
        const d = document.createElement('div');
        d.textContent = str ?? '';
        return d.innerHTML;
    }

    // ── Chart references for cleanup ─────────────────────────────────
    let _charts = [];

    function _destroyCharts() {
        _charts.forEach(c => { try { c.destroy(); } catch {} });
        _charts = [];
    }

    // ── View registry ────────────────────────────────────────────────────
    const views = {
        dashboard:    () => DashboardView.render(),
        'dashboard-f5': () => DashboardView.render(),  // backward compat alias
        'executive-cockpit': () => ExecutiveCockpitView.render(),
        'my-projects': () => MyProjectsView.render(),
        programs:     () => ProgramView.render(),
        // Legacy SCOPE views removed — FE-Sprint 1
        backlog:      () => BacklogView.render(),
        'test-planning':      () => TestPlanningView.render(),
        'test-case-detail':   (id) => TestCaseDetailView.render(id),
        'test-execution':     () => TestExecutionView.render(),
        'defect-management':  () => DefectManagementView.render(),
        'approvals':          () => ApprovalsView.render(),
        integration:  () => IntegrationView.render(),
        'data-factory': () => DataFactoryView.render(),
        cutover:      () => CutoverView.render(),
        raid:         () => RaidView.render(),
        reports:      () => ReportsView.render(),
        'suite-folders': () => SuiteFoldersView.render(),
        'env-matrix': () => EnvMatrixView.render(),
        'bdd-editor': () => BddEditorView.render(),
        'data-driven': () => DataDrivenView.render(),
        'exploratory': () => ExploratoryView.render(),
        'evidence': () => EvidenceCaptureView.render(),
        'custom-fields': () => CustomFieldsView.render(),
        'integrations': () => IntegrationsView.init(window.currentProgramId),
        'observability': () => ObservabilityView.init(),
        'gate-criteria': () => GateCriteriaView.render(document.getElementById('main-content')),
        'discover':     () => DiscoverView.render(document.getElementById('mainContent')),
        'timeline':     () => TimelineView.render(document.getElementById('mainContent')),
        'raci':         () => RaciView.render(document.getElementById('mainContent')),
        'hypercare':     () => HypercareView.render(document.getElementById('mainContent')),
        'project-setup': () => ProjectSetupView.render(),
        'ai-insights': () => AIInsightsView.render(),
        'ai-query':   () => AIQueryView.render(),
        'ai-admin':   () => AIAdminView.render(),
        // Explore Phase views
        'explore-dashboard':       () => ExploreDashboardView.render(),
        'explore-hierarchy':       () => ExploreHierarchyView.render(),
        'explore-workshops':       () => ExploreWorkshopHubView.render(),
        'explore-workshop-detail': () => ExploreWorkshopDetailView.render(),
        'explore-requirements':    () => ExploreRequirementHubView.render(),
        'knowledge-base':           () => KnowledgeBaseView.init(window.currentTenantId),
    };

    let currentView = 'programs';
    let _programOptions = [];
    let _projectOptions = [];
    let _contextEvents = [];

    // ── Program Context ─────────────────────────────────────────────────
    // Views that require a program to be selected
    const programRequiredViews = new Set([
        'dashboard', 'dashboard-f5',
        'executive-cockpit',
        'backlog', 'test-planning', 'test-execution', 'defect-management', 'approvals', 'integration', 'data-factory', 'cutover', 'raid',
        'test-case-detail',
        'reports', 'suite-folders', 'env-matrix', 'bdd-editor', 'data-driven', 'exploratory', 'evidence', 'custom-fields', 'integrations', 'observability', 'gate-criteria', 'project-setup', 'ai-insights', 'ai-query', 'discover', 'timeline', 'raci', 'hypercare',
        'explore-dashboard', 'explore-hierarchy', 'explore-workshops', 'explore-workshop-detail', 'explore-requirements',
    ]);

    const projectAwareViews = new Set([
        'project-setup',
        'explore-dashboard', 'explore-hierarchy', 'explore-workshops', 'explore-workshop-detail', 'explore-requirements',
        'test-planning', 'test-execution', 'defect-management',
        'cutover', 'hypercare', 'integration', 'data-factory',
    ]);

    function _isProjectRequiredView(viewName) {
        // Project Setup is the project-selection gateway; it must stay reachable
        // with program-only context. Programs view is always reachable.
        if (!viewName || viewName === 'programs' || viewName === 'project-setup') return false;
        return projectAwareViews.has(viewName);
    }

    function _currentTenantId() {
        const user = (typeof Auth !== 'undefined' && Auth.getUser) ? Auth.getUser() : null;
        return user ? user.tenant_id : null;
    }

    function _safeInt(value) {
        if (value === null || value === undefined || value === '') return null;
        const parsed = Number.parseInt(String(value), 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    }

    function _trackContextEvent(type, details = {}) {
        const payload = {
            type,
            details,
            ts: new Date().toISOString(),
        };
        _contextEvents.push(payload);
        if (_contextEvents.length > 100) _contextEvents = _contextEvents.slice(-100);
        if (typeof Analytics !== 'undefined' && typeof Analytics.track === 'function') {
            try {
                Analytics.track('invalid_context_event', payload);
            } catch {
                // No-op: telemetry failures must never break context resolution.
            }
        }
    }

    function _readContextFromUrl() {
        const params = new URLSearchParams(window.location.search || '');
        const hasProgramParam = params.has('program_id');
        const hasProjectParam = params.has('project_id');
        const rawProgramId = params.get('program_id');
        const rawProjectId = params.get('project_id');
        return {
            hasProgramParam,
            hasProjectParam,
            rawProgramId,
            rawProjectId,
            programId: _safeInt(rawProgramId),
            projectId: _safeInt(rawProjectId),
        };
    }

    function _syncUrlContext(options = {}) {
        const replace = options.replace !== false;
        const program = getActiveProgram();
        const project = getActiveProject();
        const params = new URLSearchParams(window.location.search || '');

        if (program) params.set('program_id', String(program.id));
        else params.delete('program_id');

        if (project) params.set('project_id', String(project.id));
        else params.delete('project_id');

        const query = params.toString();
        const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash || ''}`;
        if (replace) window.history.replaceState({}, '', nextUrl);
        else window.history.pushState({}, '', nextUrl);
    }

    function getActiveProgram() {
        const stored = localStorage.getItem('sap_active_program');
        if (!stored) return null;
        try {
            const program = JSON.parse(stored);
            const currentTenantId = _currentTenantId();
            // Prevent cross-tenant context leakage from stale localStorage.
            if (program) {
                // Legacy payloads without tenant_id are unsafe after tenant switches.
                if (!Object.prototype.hasOwnProperty.call(program, 'tenant_id')) {
                    localStorage.removeItem('sap_active_program');
                    return null;
                }
                if (program.tenant_id !== currentTenantId) {
                    localStorage.removeItem('sap_active_program');
                    return null;
                }
            }
            return program;
        } catch {
            return null;
        }
    }

    function getActiveProject() {
        const stored = localStorage.getItem('sap_active_project');
        if (!stored) return null;
        try {
            const project = JSON.parse(stored);
            const currentTenantId = _currentTenantId();
            if (!project || project.tenant_id !== currentTenantId) {
                localStorage.removeItem('sap_active_project');
                return null;
            }
            const activeProgram = getActiveProgram();
            if (!activeProgram || project.program_id !== activeProgram.id) {
                localStorage.removeItem('sap_active_project');
                return null;
            }
            return project;
        } catch {
            localStorage.removeItem('sap_active_project');
            return null;
        }
    }

    function _syncGlobalContext() {
        const prog = getActiveProgram();
        const project = getActiveProject();
        window.currentProgramId = prog ? prog.id : null;
        window.currentProjectId = project ? project.id : null;
        App.state = {
            programId: prog ? prog.id : null,
            currentProgramId: prog ? prog.id : null,
            projectId: project ? project.id : null,
            currentProjectId: project ? project.id : null,
        };
    }

    function setActiveProject(project, options = {}) {
        const activeProgram = getActiveProgram();
        if (project && activeProgram && project.program_id !== activeProgram.id) {
            localStorage.removeItem('sap_active_project');
        } else if (project) {
            localStorage.setItem('sap_active_project', JSON.stringify({
                id: project.id,
                name: project.name,
                code: project.code,
                program_id: project.program_id,
                tenant_id: _currentTenantId(),
            }));
        } else {
            localStorage.removeItem('sap_active_project');
        }
        _syncGlobalContext();
        updateContextIndicators();
        renderContextBanner();
        if (options.syncUrl !== false) _syncUrlContext({ replace: true });
        if (
            project &&
            activeProgram &&
            typeof MyProjectsView !== 'undefined' &&
            typeof MyProjectsView.recordRecentContext === 'function'
        ) {
            MyProjectsView.recordRecentContext(activeProgram.id, project.id);
        }
    }

    function setActiveProgram(program, options = {}) {
        const previousProgram = getActiveProgram();
        if (program) {
            localStorage.setItem('sap_active_program', JSON.stringify({
                id: program.id,
                name: program.name,
                status: program.status,
                project_type: program.project_type,
                tenant_id: _currentTenantId(),
            }));
        } else {
            localStorage.removeItem('sap_active_program');
        }
        const activeProject = getActiveProject();
        if (!program || !activeProject || activeProject.program_id !== program.id) {
            localStorage.removeItem('sap_active_project');
        }
        _syncGlobalContext();
        updateContextIndicators();
        updateSidebarState();
        loadProjectOptions(program ? program.id : null);
        renderContextBanner();
        if (options.syncUrl !== false) _syncUrlContext({ replace: true });
        // Refresh team member cache for new program
        TeamMemberPicker.invalidateCache();
        if (!options.silent && program && (!previousProgram || previousProgram.id !== program.id)) {
            toast(`Context switched to program "${program.name}"`, 'info');
        }
    }

    function updateContextIndicators() {
        const prog = getActiveProgram();
        const project = getActiveProject();
        const nameEl = document.getElementById('activeProgramName');
        const badge = document.getElementById('activeProgramBadge');
        const sidebarProgram = document.getElementById('sidebarActiveProgramName');
        const sidebarProject = document.getElementById('sidebarActiveProjectName');

        if (prog) {
            nameEl.textContent = prog.name;
            badge.classList.add('shell-header__program-badge--active');
            badge.title = `${prog.name} (${prog.project_type}) — Click to switch`;
        } else {
            nameEl.textContent = 'No program selected';
            badge.classList.remove('shell-header__program-badge--active');
            badge.title = 'Click to select a program';
        }
        if (sidebarProgram) sidebarProgram.textContent = prog ? prog.name : '—';
        if (sidebarProject) sidebarProject.textContent = project ? project.name : '—';
    }

    function _buildSelectOptions(items, valueKey = 'id', labelBuilder = (x) => x.name) {
        return ['<option value="">Select</option>'].concat(
            items.map(item => `<option value="${esc(item[valueKey])}">${esc(labelBuilder(item))}</option>`)
        ).join('');
    }

    async function loadProgramOptions() {
        try {
            const list = await API.get('/programs');
            _programOptions = Array.isArray(list) ? list : [];
        } catch {
            _programOptions = [];
        }
        renderContextSelectors();
    }

    async function loadProjectOptions(programId) {
        if (!programId) {
            _projectOptions = [];
            renderContextSelectors();
            return;
        }
        try {
            const list = await API.get(`/programs/${programId}/projects`);
            _projectOptions = Array.isArray(list) ? list : [];
        } catch {
            _projectOptions = [];
        }
        const activeProject = getActiveProject();
        if (activeProject && !_projectOptions.some(p => Number(p.id) === Number(activeProject.id))) {
            setActiveProject(null);
            toast('Selected project no longer belongs to this program. Please select again.', 'warning');
        }
        renderContextSelectors();
    }

    async function _resolveContextFromUrlOnBoot() {
        const parsed = _readContextFromUrl();
        const hasAnyContextParam = parsed.hasProgramParam || parsed.hasProjectParam;
        if (!hasAnyContextParam) return;

        if (parsed.hasProgramParam && parsed.rawProgramId && parsed.programId === null) {
            _trackContextEvent('invalid_program_param', { value: parsed.rawProgramId });
            toast('Invalid program_id in URL. Stored context was used instead.', 'warning');
        }
        if (parsed.hasProjectParam && parsed.rawProjectId && parsed.projectId === null) {
            _trackContextEvent('invalid_project_param', { value: parsed.rawProjectId });
            toast('Invalid project_id in URL. Please select a valid project.', 'warning');
        }
        if (!parsed.programId && parsed.projectId) {
            _trackContextEvent('invalid_context_missing_program', { project_id: parsed.projectId });
            toast('project_id requires a valid program_id. Please select a program.', 'warning');
            _syncUrlContext({ replace: true });
            return;
        }

        if (parsed.programId) {
            const urlProgram = _programOptions.find((p) => Number(p.id) === Number(parsed.programId)) || null;
            if (!urlProgram) {
                _trackContextEvent('program_not_found_or_unauthorized', { program_id: parsed.programId });
                toast('Program in URL is not available for your tenant. Fallback applied.', 'warning');
                _syncUrlContext({ replace: true });
                return;
            }
            setActiveProgram(urlProgram, { silent: true, syncUrl: false });
            await loadProjectOptions(urlProgram.id);
        }

        if (parsed.projectId) {
            const urlProject = _projectOptions.find((p) => Number(p.id) === Number(parsed.projectId)) || null;
            if (!urlProject) {
                _trackContextEvent('project_not_found_or_mismatch', {
                    program_id: parsed.programId,
                    project_id: parsed.projectId,
                });
                setActiveProject(null, { syncUrl: false });
                toast('Project in URL is invalid for selected program. Please choose a valid project.', 'warning');
                _syncUrlContext({ replace: true });
                return;
            }
            setActiveProject(urlProject, { syncUrl: false });
        }

        _syncUrlContext({ replace: true });
    }

    function renderContextSelectors() {
        const programSelect = document.getElementById('headerProgramSelect');
        const projectSelect = document.getElementById('headerProjectSelect');
        if (!programSelect || !projectSelect) return;

        const activeProgram = getActiveProgram();
        const activeProject = getActiveProject();

        programSelect.innerHTML = _buildSelectOptions(
            _programOptions,
            'id',
            (p) => p.name || `Program ${p.id}`
        );
        programSelect.value = activeProgram ? String(activeProgram.id) : '';

        projectSelect.disabled = !activeProgram;
        projectSelect.innerHTML = _buildSelectOptions(
            _projectOptions,
            'id',
            (p) => `${p.code || 'PRJ'} - ${p.name || `Project ${p.id}`}`
        );
        projectSelect.value = activeProject ? String(activeProject.id) : '';
    }

    function bindContextSelectorEvents() {
        const programSelect = document.getElementById('headerProgramSelect');
        const projectSelect = document.getElementById('headerProjectSelect');
        if (!programSelect || !projectSelect) return;

        programSelect.addEventListener('change', async (event) => {
            const id = Number(event.target.value) || null;
            const selected = _programOptions.find((p) => Number(p.id) === id) || null;
            setActiveProgram(selected);
            if (!selected) {
                toast('Program context cleared', 'info');
                return;
            }
            await loadProjectOptions(selected.id);
        });

        projectSelect.addEventListener('change', (event) => {
            const id = Number(event.target.value) || null;
            const selected = _projectOptions.find((p) => Number(p.id) === id) || null;
            setActiveProject(selected);
            if (selected) {
                toast(`Project "${selected.name}" selected`, 'success');
            } else {
                toast('Project selection cleared', 'info');
            }
        });
    }

    function updateSidebarState() {
        const hasProgram = !!getActiveProgram();
        const hasProject = !!getActiveProject();
        document.querySelectorAll('.sidebar__item').forEach(item => {
            const view = item.dataset.view;
            if (programRequiredViews.has(view)) {
                const disabled = !hasProgram || (_isProjectRequiredView(view) && !hasProject);
                item.classList.toggle('sidebar__item--disabled', disabled);
            }
        });

        // Hide AI suggestion badge button when no program selected
        const suggBtn = document.querySelector('.shell-header__actions .shell-header__icon-btn[title="AI Suggestions"]');
        if (suggBtn) {
            suggBtn.style.opacity = hasProgram ? '1' : '0.3';
            suggBtn.style.pointerEvents = hasProgram ? 'auto' : 'none';
        }
        const suggDropdown = document.getElementById('suggDropdown');
        if (suggDropdown && !hasProgram) suggDropdown.style.display = 'none';
    }

    function renderContextBanner() {
        const main = document.getElementById('mainContent');
        if (!main) return;
        const existing = document.getElementById('contextGuardBanner');
        if (existing) existing.remove();

        if (currentView === 'programs') return;
        if (!programRequiredViews.has(currentView)) return;

        const program = getActiveProgram();
        const project = getActiveProject();
        const banner = document.createElement('div');
        banner.id = 'contextGuardBanner';
        banner.className = 'context-guard-banner';

        if (!program) {
            banner.innerHTML = `
                <span>Program context is missing. Select a program to continue safely.</span>
                <button onclick="App.navigate('programs')">Select Program</button>
            `;
        } else if (!project && _isProjectRequiredView(currentView)) {
            banner.innerHTML = `
                <span>Program: <strong>${esc(program.name)}</strong>. Project is required for this screen.</span>
                <button onclick="document.getElementById('headerProjectSelect')?.focus()">Select Project</button>
            `;
        } else {
            banner.innerHTML = `
                <span>Context: <strong>${esc(program.name)}</strong> / <strong>${esc(project ? project.name : 'No project')}</strong></span>
                <button onclick="App.navigate('programs')">Change</button>
            `;
        }
        main.prepend(banner);
    }

    // ── Navigation ───────────────────────────────────────────────────────
    function navigate(viewName, ...args) {
        if (!views[viewName]) return;

        // Guard: program-required views need an active program
        if (programRequiredViews.has(viewName) && !getActiveProgram()) {
            toast('Please select a program first', 'warning');
            navigate('programs');
            return;
        }
        if (_isProjectRequiredView(viewName) && !getActiveProject()) {
            toast('Please select a project first', 'warning');
            navigate('project-setup');
            return;
        }

        // Cleanup previous charts
        _destroyCharts();

        currentView = viewName;

        // Update sidebar active state
        document.querySelectorAll('.sidebar__item').forEach(item => {
            item.classList.toggle('active', item.dataset.view === viewName);
        });

        // Render the view
        views[viewName](...args);
        renderContextBanner();

        // Page transition animation (UI-S09-T04)
        const main = document.getElementById('mainContent');
        if (main) {
            main.classList.remove('pg-view-enter');
            void main.offsetWidth; // force reflow to restart animation
            main.classList.add('pg-view-enter');
        }
    }

    // ── Placeholder for future modules ───────────────────────────────────
    function placeholder(title, sprint) {
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="empty-state">
                <div class="empty-state__icon">🚧</div>
                <div class="empty-state__title">${esc(title)}</div>
                <p>This module will be implemented in <strong>${esc(sprint)}</strong>.</p>
            </div>
        `;
    }

    // ── Toast notifications ──────────────────────────────────────────────
    function toast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    // ── Modal ────────────────────────────────────────────────────────────
    function openModal(html) {
        document.getElementById('modalContainer').innerHTML = html;
        document.getElementById('modalOverlay').classList.add('open');
    }

    function closeModal() {
        document.getElementById('modalOverlay').classList.remove('open');
    }

    // ── Init ─────────────────────────────────────────────────────────────
    async function init() {
        // Sidebar click handlers
        document.querySelectorAll('.sidebar__item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                if (view) navigate(view);
            });
        });

        // Close modal on overlay click
        document.getElementById('modalOverlay').addEventListener('click', e => {
            if (e.target.id === 'modalOverlay') closeModal();
        });

        // Close modal on ESC key
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && document.getElementById('modalOverlay').classList.contains('open')) {
                closeModal();
            }
        });

        // Initialize notification panel (Sprint 6)
        if (typeof NotificationPanel !== 'undefined') {
            NotificationPanel.init();
        }

        // Initialize AI suggestion badge (Sprint 7)
        if (typeof SuggestionBadge !== 'undefined') {
            SuggestionBadge.init();
        }

        // Auth guard — redirect to login if not authenticated
        if (typeof Auth !== 'undefined' && !Auth.guard()) {
            return; // guard() will redirect
        }

        // Initialize profile dropdown (replaces demo user switcher)
        _initProfileDropdown();

        // Initialize role-based navigation from JWT user
        if (typeof RoleNav !== 'undefined') {
            const user = Auth.getUser();
            if (user) {
                RoleNav.setUser({
                    id: String(user.id),
                    name: user.full_name || user.email,
                    default_role: (user.roles && user.roles[0]) || 'viewer',
                });
            }
            RoleNav.preload();
        }

        // Set up program/project context from localStorage
        _syncGlobalContext();
        updateContextIndicators();
        updateSidebarState();
        bindContextSelectorEvents();
        await loadProgramOptions();
        await _resolveContextFromUrlOnBoot();
        const activeProgram = getActiveProgram();
        if (activeProgram) {
            await loadProjectOptions(activeProgram.id);
        } else {
            await loadProjectOptions(null);
        }

        // Initialize sidebar collapse (UI-S03-T03)
        initSidebarCollapse();

        // Initialize a11y utilities (UI-S09-T02/T03)
        if (typeof PGa11y !== 'undefined') {
            PGa11y.initThemeToggle();
            PGa11y.initModalFocusTrap();
        }

        // Render default view
        navigate('programs');
    }

    // ── Sidebar Collapse (UI-S03-T03) ─────────────────────────────

    function initSidebarCollapse() {
        const sidebar = document.getElementById('sidebar');
        const collapseBtn = document.getElementById('sidebarCollapseBtn');
        if (!sidebar || !collapseBtn) return;

        const stored = localStorage.getItem('pg_sidebar_collapsed') === 'true';
        if (stored) sidebar.classList.add('sidebar--collapsed');

        collapseBtn.addEventListener('click', () => {
            const isCollapsed = sidebar.classList.toggle('sidebar--collapsed');
            localStorage.setItem('pg_sidebar_collapsed', isCollapsed);
        });
    }

    // ── Profile Dropdown ──────────────────────────────────────────

    function _initProfileDropdown() {
        const btn = document.getElementById('profileBtn');
        const menu = document.getElementById('profileMenu');
        if (!btn || !menu) return;

        // Populate from stored JWT user
        _updateProfileDisplay();

        // Fetch fresh profile from backend (async)
        _refreshProfile();

        // Toggle dropdown
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('open');
        });

        // Close on outside click
        document.addEventListener('click', () => menu.classList.remove('open'));
    }

    function _updateProfileDisplay() {
        const user = Auth.getUser();
        if (!user) return;

        const fullName = user.full_name || user.email || 'User';
        const initials = _getInitials(fullName);
        const email = user.email || '';
        const roles = user.roles || [];
        const roleName = roles.length ? roles.map(r => r.replace(/_/g, ' ')).join(', ') : 'User';

        const avatarEl = document.getElementById('profileAvatar');
        const nameEl = document.getElementById('profileName');
        const fullNameEl = document.getElementById('profileFullName');
        const emailEl = document.getElementById('profileEmail');
        const roleEl = document.getElementById('profileRole');

        if (avatarEl) avatarEl.textContent = initials;
        if (nameEl) nameEl.textContent = fullName.split(' ')[0]; // First name only
        if (fullNameEl) fullNameEl.textContent = fullName;
        if (emailEl) emailEl.textContent = email;
        if (roleEl) roleEl.textContent = roleName;
    }

    async function _refreshProfile() {
        try {
            const data = await Auth.fetchUserProfile();
            if (data && data.user) {
                _updateProfileDisplay();
                // Update tenant info
                if (data.tenant) {
                    const tenantEl = document.getElementById('profileTenantName');
                    if (tenantEl) tenantEl.textContent = data.tenant.name || data.tenant.slug;
                }
            }
        } catch { /* ignore — stored user data is fine */ }
    }

    function _getInitials(name) {
        if (!name) return '?';
        const parts = name.trim().split(/\s+/);
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    }

    // Start
    document.addEventListener('DOMContentLoaded', init);

    // Public API
    return {
        navigate, toast, openModal, closeModal,
        getActiveProgram, setActiveProgram,
        getActiveProject, setActiveProject,
        syncUrlContext: _syncUrlContext,
        getContextEvents: () => _contextEvents.slice(),
        updateProgramBadge: updateContextIndicators,
        updateSidebarState,
        renderContextBanner,
        state: {},
    };
})();
