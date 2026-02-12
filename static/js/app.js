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
        'test-execution':     () => TestExecutionView.render(),
        'defect-management':  () => DefectManagementView.render(),
        integration:  () => IntegrationView.render(),
        'data-factory': () => DataFactoryView.render(),
        cutover:      () => placeholder('Cutover Hub', 'Sprint 13'),
        raid:         () => RaidView.render(),
        reports:      () => ReportsView.render(),
        'project-setup': () => ProjectSetupView.render(),
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
        'backlog', 'test-planning', 'test-execution', 'defect-management', 'integration', 'data-factory', 'cutover', 'raid',
        'reports', 'project-setup', 'ai-query',
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
    function navigate(viewName) {
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
        views[viewName]();
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

        // Initialize role-based navigation (WR-3.1)
        if (typeof RoleNav !== 'undefined') {
            _initUserSwitcher();
            RoleNav.preload();
        }

        // Set up program context from localStorage
        updateProgramBadge();
        updateSidebarState();

        // Render default view
        navigate('dashboard');
    }

    // ── Demo User Switcher (WR-3.1) ─────────────────────────────────
    const DEMO_USERS = [
        { id: 'demo-pm',         name: 'Ahmet (PM)',         default_role: 'pm' },
        { id: 'demo-lead',       name: 'Ayşe (Module Lead)', default_role: 'module_lead' },
        { id: 'demo-facilitator', name: 'Fatma (Facilitator)', default_role: 'facilitator' },
        { id: 'demo-bpo',        name: 'Mehmet (BPO)',       default_role: 'bpo' },
        { id: 'demo-tech',       name: 'Elif (Tech Lead)',   default_role: 'tech_lead' },
        { id: 'demo-tester',     name: 'Can (Tester)',       default_role: 'tester' },
        { id: 'demo-viewer',     name: 'Zeynep (Viewer)',    default_role: 'viewer' },
    ];

    function _initUserSwitcher() {
        const btn = document.getElementById('userSwitcherBtn');
        const dd = document.getElementById('userSwitcherDropdown');
        if (!btn || !dd) return;

        // Set default demo user if none
        if (!RoleNav.getUser()) {
            RoleNav.setUser(DEMO_USERS[0]);
        }
        _updateUserLabel();

        // Build dropdown items
        dd.innerHTML = DEMO_USERS.map(u => {
            const active = (RoleNav.getUser()?.id === u.id) ? ' user-switcher__item--active' : '';
            return `<div class="user-switcher__item${active}" data-uid="${u.id}">
                <span>${esc(u.name)}</span>
                <span class="user-switcher__role">${u.default_role}</span>
            </div>`;
        }).join('');

        // Toggle dropdown
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            dd.classList.toggle('open');
        });

        // Select user
        dd.addEventListener('click', async (e) => {
            const item = e.target.closest('.user-switcher__item');
            if (!item) return;
            const uid = item.dataset.uid;
            const user = DEMO_USERS.find(u => u.id === uid);
            if (user) {
                RoleNav.setUser(user);
                await RoleNav.preload();
                _updateUserLabel();
                _initUserSwitcher();  // rebuild dropdown active state
                dd.classList.remove('open');
                // Re-apply permission guards on visible DOM
                RoleNav.applyToDOM();
                toast(`Switched to ${user.name}`, 'info');
            }
        });

        // Close on outside click
        document.addEventListener('click', () => dd.classList.remove('open'));
    }

    function _updateUserLabel() {
        const label = document.getElementById('userSwitcherLabel');
        if (label) label.textContent = RoleNav.getUserDisplay();
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
