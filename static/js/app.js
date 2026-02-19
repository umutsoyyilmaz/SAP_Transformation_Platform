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
        dashboard:    () => renderDashboard(),
        'executive-cockpit': () => ExecutiveCockpitView.render(),
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
        'dashboard-f5': () => DashboardView.render(),
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
    };

    let currentView = 'dashboard';

    // ── Program Context ─────────────────────────────────────────────────
    // Views that require a program to be selected
    const programRequiredViews = new Set([
        'executive-cockpit',
        'backlog', 'test-planning', 'test-execution', 'defect-management', 'approvals', 'integration', 'data-factory', 'cutover', 'raid',
        'test-case-detail',
        'reports', 'dashboard-f5', 'suite-folders', 'env-matrix', 'bdd-editor', 'data-driven', 'exploratory', 'evidence', 'custom-fields', 'integrations', 'observability', 'gate-criteria', 'project-setup', 'ai-insights', 'ai-query',
        'explore-dashboard', 'explore-hierarchy', 'explore-workshops', 'explore-workshop-detail', 'explore-requirements',
    ]);

    function getActiveProgram() {
        const stored = localStorage.getItem('sap_active_program');
        if (!stored) return null;
        try { return JSON.parse(stored); } catch { return null; }
    }

    function setActiveProgram(program) {
        if (program) {
            localStorage.setItem('sap_active_program', JSON.stringify({
                id: program.id,
                name: program.name,
                status: program.status,
                project_type: program.project_type,
            }));
        } else {
            localStorage.removeItem('sap_active_program');
        }
        updateProgramBadge();
        updateSidebarState();
        // Refresh team member cache for new program
        TeamMemberPicker.invalidateCache();
    }

    function updateProgramBadge() {
        const prog = getActiveProgram();
        const nameEl = document.getElementById('activeProgramName');
        const badge = document.getElementById('activeProgramBadge');
        if (prog) {
            nameEl.textContent = prog.name;
            badge.classList.add('shell-header__program-badge--active');
            badge.title = `${prog.name} (${prog.project_type}) — Click to switch`;
        } else {
            nameEl.textContent = 'No program selected';
            badge.classList.remove('shell-header__program-badge--active');
            badge.title = 'Click to select a program';
        }
    }

    function updateSidebarState() {
        const hasProgram = !!getActiveProgram();
        document.querySelectorAll('.sidebar__item').forEach(item => {
            const view = item.dataset.view;
            if (programRequiredViews.has(view)) {
                item.classList.toggle('sidebar__item--disabled', !hasProgram);
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

    // ── Navigation ───────────────────────────────────────────────────────
    function navigate(viewName, ...args) {
        if (!views[viewName]) return;

        // Guard: program-required views need an active program
        if (programRequiredViews.has(viewName) && !getActiveProgram()) {
            toast('Please select a program first', 'warning');
            navigate('programs');
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
    }

    // ── Dashboard (Program-Specific) ─────────────────────────────────────
    async function renderDashboard() {
        const main = document.getElementById('mainContent');
        const prog = getActiveProgram();

        if (!prog) {
            main.innerHTML = `
                <div class="page-header"><h1>Dashboard</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">📋</div>
                    <div class="empty-state__title">Welcome to SAP Transformation Platform</div>
                    <p>Select a program to get started.</p>
                    <br>
                    <button class="btn btn-primary" onclick="App.navigate('programs')">
                        Go to Programs
                    </button>
                </div>
            `;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>${esc(prog.name)} — Dashboard</h1>
                <span class="badge badge-${esc(prog.status)}">${esc(prog.status)}</span>
            </div>
            <div class="kpi-row" id="kpiRow">
                <!-- Explore -->
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiWorkshops">—</div>
                    <div class="kpi-card__label">Workshops</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiWsCompletion">—</div>
                    <div class="kpi-card__label">WS Completion</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiRequirements">—</div>
                    <div class="kpi-card__label">Requirements</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiOpenItems">—</div>
                    <div class="kpi-card__label">Open Items</div>
                </div>
                <!-- Delivery -->
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiBacklog">—</div>
                    <div class="kpi-card__label">Backlog Items</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiDefects">—</div>
                    <div class="kpi-card__label">Open Defects</div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h2>Quick Navigation</h2>
                </div>
                <div class="dashboard-quick-nav">
                    <button class="btn btn-secondary" onclick="App.navigate('explore-dashboard')">📊 Explore Dashboard</button>
                    <button class="btn btn-secondary" onclick="App.navigate('explore-hierarchy')">🏗️ Process Hierarchy</button>
                    <button class="btn btn-secondary" onclick="App.navigate('explore-workshops')">📋 Workshops</button>
                    <button class="btn btn-secondary" onclick="App.navigate('explore-requirements')">📝 Requirements</button>
                    <button class="btn btn-secondary" onclick="App.navigate('backlog')">⚙️ Backlog</button>
                    <button class="btn btn-secondary" onclick="App.navigate('test-planning')">📋 Test Planning</button>
                    <button class="btn btn-secondary" onclick="App.navigate('test-execution')">▶️ Test Execution</button>
                    <button class="btn btn-secondary" onclick="App.navigate('defect-management')">🐛 Defects</button>
                    <button class="btn btn-secondary" onclick="App.navigate('raid')">⚠️ RAID</button>
                </div>
            </div>
        `;

        // Load program-specific KPIs
        try {
            const pid = prog.id;
            const [wsStats, reqStats, oiStats, backlogStats, defectRes] = await Promise.allSettled([
                API.get(`/explore/workshops/stats?project_id=${pid}`),
                API.get(`/explore/requirements/stats?project_id=${pid}`),
                API.get(`/explore/open-items/stats?project_id=${pid}`),
                API.get(`/programs/${pid}/backlog/stats`),
                API.get(`/programs/${pid}/testing/defects?per_page=1`),
            ]);

            if (wsStats.status === 'fulfilled') {
                const ws = wsStats.value;
                document.getElementById('kpiWorkshops').textContent = ws.total || 0;
                document.getElementById('kpiWsCompletion').textContent = (ws.completion_pct || 0) + '%';
            }

            if (reqStats.status === 'fulfilled') {
                const rs = reqStats.value;
                document.getElementById('kpiRequirements').textContent = rs.total || 0;
            }

            if (oiStats.status === 'fulfilled') {
                const oi = oiStats.value;
                document.getElementById('kpiOpenItems').textContent = oi.total || 0;
            }

            if (backlogStats.status === 'fulfilled') {
                const bs = backlogStats.value;
                document.getElementById('kpiBacklog').textContent = bs.total_items ?? bs.total ?? 0;
            }

            if (defectRes.status === 'fulfilled') {
                const dr = defectRes.value;
                document.getElementById('kpiDefects').textContent = dr.total || 0;
            }
        } catch (err) {
            console.warn('Dashboard KPI load error:', err);
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
    function init() {
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

        // Set up program context from localStorage
        updateProgramBadge();
        updateSidebarState();

        // Render default view
        navigate('dashboard');
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
        updateProgramBadge, updateSidebarState,
    };
})();
