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
        requirements: () => RequirementView.render(),
        backlog:      () => BacklogView.render(),
        testing:      () => TestingView.render(),
        integration:  () => placeholder('Integration Factory', 'Sprint 9'),
        'data-factory': () => placeholder('Data Factory', 'Sprint 10'),
        cutover:      () => placeholder('Cutover Hub', 'Sprint 13'),
        raid:         () => RaidView.render(),
        reports:      () => placeholder('Reports', 'Sprint 11'),
        'ai-query':   () => AIQueryView.render(),
        'ai-admin':   () => AIAdminView.render(),
    };

    let currentView = 'dashboard';

    // ── Navigation ───────────────────────────────────────────────────────
    function navigate(viewName) {
        if (!views[viewName]) return;
        currentView = viewName;

        // Update sidebar active state
        document.querySelectorAll('.sidebar__item').forEach(item => {
            item.classList.toggle('active', item.dataset.view === viewName);
        });

        // Render the view
        views[viewName]();
    }

    // ── Dashboard ────────────────────────────────────────────────────────
    async function renderDashboard() {
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <h1>Dashboard</h1>
            </div>
            <div class="kpi-row" id="kpiRow">
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiTotalPrograms">—</div>
                    <div class="kpi-card__label">Total Programs</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiActive">—</div>
                    <div class="kpi-card__label">Active</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiPlanning">—</div>
                    <div class="kpi-card__label">Planning</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" id="kpiCompleted">—</div>
                    <div class="kpi-card__label">Completed</div>
                </div>
            </div>
            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-header"><h2>Program Status Distribution</h2></div>
                    <canvas id="statusChart" height="220"></canvas>
                </div>
                <div class="card">
                    <div class="card-header"><h2>Programs by Type</h2></div>
                    <canvas id="typeChart" height="220"></canvas>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <h2>Recent Programs</h2>
                    <button class="btn btn-primary" onclick="App.navigate('programs')">View All</button>
                </div>
                <div id="recentProgramsList"></div>
            </div>
        `;

        try {
            const programs = await API.get('/programs');
            const active = programs.filter(p => p.status === 'active').length;
            const planning = programs.filter(p => p.status === 'planning').length;
            const completed = programs.filter(p => p.status === 'completed').length;
            const onHold = programs.filter(p => p.status === 'on_hold').length;
            const cancelled = programs.filter(p => p.status === 'cancelled').length;

            document.getElementById('kpiTotalPrograms').textContent = programs.length;
            document.getElementById('kpiActive').textContent = active;
            document.getElementById('kpiPlanning').textContent = planning;
            document.getElementById('kpiCompleted').textContent = completed;

            // Status distribution doughnut chart
            if (typeof Chart !== 'undefined') {
                new Chart(document.getElementById('statusChart'), {
                    type: 'doughnut',
                    data: {
                        labels: ['Active', 'Planning', 'Completed', 'On Hold', 'Cancelled'],
                        datasets: [{
                            data: [active, planning, completed, onHold, cancelled],
                            backgroundColor: ['#0070f2', '#e76500', '#30914c', '#a9b4be', '#cc1919'],
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'bottom' } },
                    },
                });

                // Programs by type bar chart
                const typeCount = {};
                programs.forEach(p => { typeCount[p.project_type] = (typeCount[p.project_type] || 0) + 1; });
                new Chart(document.getElementById('typeChart'), {
                    type: 'bar',
                    data: {
                        labels: Object.keys(typeCount),
                        datasets: [{
                            label: 'Programs',
                            data: Object.values(typeCount),
                            backgroundColor: '#0070f2',
                            borderRadius: 6,
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
                    },
                });
            }

            const recent = programs.slice(0, 5);
            if (recent.length === 0) {
                document.getElementById('recentProgramsList').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state__icon">📋</div>
                        <div class="empty-state__title">No programs yet</div>
                        <p>Create your first SAP transformation program to get started.</p>
                        <br>
                        <button class="btn btn-primary" onclick="App.navigate('programs')">
                            + Create Program
                        </button>
                    </div>
                `;
            } else {
                document.getElementById('recentProgramsList').innerHTML = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Methodology</th>
                                <th>Status</th>
                                <th>SAP Product</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${recent.map(p => `
                                <tr style="cursor:pointer" onclick="App.navigate('programs');setTimeout(()=>ProgramView.openDetail(${p.id}),100)">
                                    <td><strong>${esc(p.name)}</strong></td>
                                    <td>${esc(p.project_type)}</td>
                                    <td>${esc(p.methodology)}</td>
                                    <td><span class="badge badge-${esc(p.status)}">${esc(p.status)}</span></td>
                                    <td>${esc(p.sap_product)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }

            // Update global project selector
            updateProjectSelector(programs);
        } catch (err) {
            document.getElementById('recentProgramsList').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
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

    // ── Global Project Selector ──────────────────────────────────────────
    async function updateProjectSelector(programs) {
        const selector = document.getElementById('globalProjectSelector');
        if (!programs) {
            try { programs = await API.get('/programs'); } catch { programs = []; }
        }
        selector.innerHTML = '<option value="">Select Program...</option>' +
            programs.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
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

        // Initialize notification panel (Sprint 6)
        if (typeof NotificationPanel !== 'undefined') {
            NotificationPanel.init();
        }

        // Initialize AI suggestion badge (Sprint 7)
        if (typeof SuggestionBadge !== 'undefined') {
            SuggestionBadge.init();
        }

        // Render default view
        navigate('dashboard');
    }

    // Start
    document.addEventListener('DOMContentLoaded', init);

    // Public API
    return { navigate, toast, openModal, closeModal, updateProjectSelector };
})();
