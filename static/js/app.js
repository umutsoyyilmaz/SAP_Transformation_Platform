/**
 * SAP Transformation Management Platform
 * SPA Router — Handles sidebar navigation and view rendering.
 */

const App = (() => {
    // ── View registry ────────────────────────────────────────────────────
    const views = {
        dashboard:    () => renderDashboard(),
        programs:     () => ProgramView.render(),
        // Future Sprint views — placeholder
        scenarios:    () => placeholder('Scenarios', 'Sprint 3'),
        requirements: () => placeholder('Requirements', 'Sprint 3'),
        backlog:      () => placeholder('Backlog Workbench', 'Sprint 4'),
        testing:      () => placeholder('Test Hub', 'Sprint 5'),
        integration:  () => placeholder('Integration Factory', 'Sprint 9'),
        'data-factory': () => placeholder('Data Factory', 'Sprint 10'),
        cutover:      () => placeholder('Cutover Hub', 'Sprint 13'),
        raid:         () => placeholder('RAID', 'Sprint 6'),
        reports:      () => placeholder('Reports', 'Sprint 11'),
        'ai-query':   () => placeholder('AI Query', 'Sprint 8'),
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
            document.getElementById('kpiTotalPrograms').textContent = programs.length;
            document.getElementById('kpiActive').textContent =
                programs.filter(p => p.status === 'active').length;
            document.getElementById('kpiPlanning').textContent =
                programs.filter(p => p.status === 'planning').length;
            document.getElementById('kpiCompleted').textContent =
                programs.filter(p => p.status === 'completed').length;

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
                                <th>Status</th>
                                <th>SAP Product</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${recent.map(p => `
                                <tr onclick="App.navigate('programs')">
                                    <td><strong>${p.name}</strong></td>
                                    <td>${p.project_type}</td>
                                    <td><span class="badge badge-${p.status}">${p.status}</span></td>
                                    <td>${p.sap_product}</td>
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
            programs.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
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

        // Render default view
        navigate('dashboard');
    }

    // Start
    document.addEventListener('DOMContentLoaded', init);

    // Public API
    return { navigate, toast, openModal, closeModal, updateProjectSelector };
})();
