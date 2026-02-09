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

    // ── View registry ────────────────────────────────────────────────────
    const views = {
        dashboard:    () => renderDashboard(),
        programs:     () => ProgramView.render(),
        // Future Sprint views — placeholder
        scenarios:    () => ScenarioView.render(),
        analysis:     () => AnalysisView.render(),
        requirements: () => RequirementView.render(),
        backlog:      () => BacklogView.render(),
        testing:      () => TestingView.render(),
        integration:  () => IntegrationView.render(),
        'data-factory': () => placeholder('Data Factory', 'Sprint 10'),
        cutover:      () => placeholder('Cutover Hub', 'Sprint 13'),
        raid:         () => RaidView.render(),
        reports:      () => placeholder('Reports', 'Sprint 11'),
        'ai-query':   () => AIQueryView.render(),
        'ai-admin':   () => AIAdminView.render(),
    };

    let currentView = 'dashboard';

    // ── Program Context ─────────────────────────────────────────────────
    // Views that require a program to be selected
    const programRequiredViews = new Set([
        'scenarios', 'analysis', 'requirements', 'backlog', 'testing',
        'integration', 'data-factory', 'cutover', 'raid',
        'reports', 'ai-query',
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
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiScenarios">—</div>
                    <div class="kpi-card__label">Scenarios</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiRequirements">—</div>
                    <div class="kpi-card__label">Requirements</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiBacklog">—</div>
                    <div class="kpi-card__label">Backlog Items</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiDefects">—</div>
                    <div class="kpi-card__label">Open Defects</div>
                </div>
            </div>
            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-header"><h2>Requirement Fit/Gap</h2></div>
                    <canvas id="fitGapChart" height="220"></canvas>
                </div>
                <div class="card">
                    <div class="card-header"><h2>Backlog by Status</h2></div>
                    <canvas id="backlogChart" height="220"></canvas>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h2>Quick Navigation</h2>
                </div>
                <div class="dashboard-quick-nav">
                    <button class="btn btn-secondary" onclick="App.navigate('scenarios')">🎯 Scenarios</button>
                    <button class="btn btn-secondary" onclick="App.navigate('analysis')">🔬 Analysis Hub</button>
                    <button class="btn btn-secondary" onclick="App.navigate('requirements')">📝 Requirements</button>
                    <button class="btn btn-secondary" onclick="App.navigate('backlog')">⚙️ Backlog</button>
                    <button class="btn btn-secondary" onclick="App.navigate('testing')">🧪 Test Hub</button>
                    <button class="btn btn-secondary" onclick="App.navigate('raid')">⚠️ RAID</button>
                </div>
            </div>
        `;

        // Load program-specific KPIs
        try {
            const pid = prog.id;
            const [scenarios, reqStats, backlogStats, defects] = await Promise.allSettled([
                API.get(`/programs/${pid}/scenarios`),
                API.get(`/programs/${pid}/requirements/stats`),
                API.get(`/programs/${pid}/backlog/stats`),
                API.get(`/programs/${pid}/testing/defects`),
            ]);

            if (scenarios.status === 'fulfilled') {
                document.getElementById('kpiScenarios').textContent = scenarios.value.length ?? 0;
            }

            if (reqStats.status === 'fulfilled') {
                const rs = reqStats.value;
                document.getElementById('kpiRequirements').textContent = rs.total ?? 0;
                // Fit/Gap chart
                if (typeof Chart !== 'undefined' && rs.by_fit_gap) {
                    new Chart(document.getElementById('fitGapChart'), {
                        type: 'doughnut',
                        data: {
                            labels: Object.keys(rs.by_fit_gap),
                            datasets: [{ data: Object.values(rs.by_fit_gap), backgroundColor: ['#30914c','#e76500','#0070f2','#a9b4be'] }],
                        },
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
                    });
                }
            }

            if (backlogStats.status === 'fulfilled') {
                const bs = backlogStats.value;
                document.getElementById('kpiBacklog').textContent = bs.total ?? 0;
                // Backlog by status chart
                if (typeof Chart !== 'undefined' && bs.by_status) {
                    new Chart(document.getElementById('backlogChart'), {
                        type: 'bar',
                        data: {
                            labels: Object.keys(bs.by_status),
                            datasets: [{ label: 'Items', data: Object.values(bs.by_status), backgroundColor: '#0070f2', borderRadius: 6 }],
                        },
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
                    });
                }
            }

            if (defects.status === 'fulfilled') {
                const openDefects = (defects.value || []).filter(d => d.status !== 'closed' && d.status !== 'cancelled');
                document.getElementById('kpiDefects').textContent = openDefects.length;
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
                <div class="empty-state__title">${title}</div>
                <p>This module will be implemented in <strong>${sprint}</strong>.</p>
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

        // Set up program context from localStorage
        updateProgramBadge();
        updateSidebarState();

        // Render default view
        navigate('dashboard');
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
