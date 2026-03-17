/**
 * Workspace Dashboard
 * Operational gadget workspace for day-to-day program delivery.
 */
const DashboardView = (() => {
    'use strict';

    let gadgets = [];
    let gadgetTypes = [];
    let layoutId = null;
    let chartInstances = [];

    function esc(value) {
        const d = document.createElement('div');
        d.textContent = value ?? '';
        return d.innerHTML;
    }

    function _destroyCharts() {
        chartInstances.forEach((chart) => { try { chart.destroy(); } catch (_) {} });
        chartInstances = [];
    }

    function _defaultGadgets() {
        return [
            { type: 'health_score', size: '1x1' },
            { type: 'kpi_strip', size: '2x1' },
            { type: 'action_items', size: '1x1' },
            { type: 'audit_activity', size: '2x1' },
            { type: 'pass_rate_gauge', size: '1x1' },
            { type: 'execution_trend', size: '2x1' },
            { type: 'defect_by_severity', size: '1x1' },
            { type: 'open_vs_closed', size: '1x1' },
            { type: 'cycle_progress', size: '2x1' },
            { type: 'recent_activity', size: '2x1' },
        ];
    }

    function _projectDisplay(project) {
        if (!project) return '';
        const code = String(project.code || '').trim();
        const name = String(project.name || '').trim();
        const isDefault = code.toUpperCase() === 'DEFAULT'
            || name.toUpperCase() === 'DEFAULT'
            || /(?:^| - )default$/i.test(name);
        if (isDefault) return 'Default';
        return name || code || 'Selected';
    }

    function _renderShell(prog, project, bodyHtml, opts = {}) {
        const activeGadgets = gadgets.length || _defaultGadgets().length;
        const projectDisplay = _projectDisplay(project);
        const spotlights = opts.spotlights || [
            { value: activeGadgets, label: 'Active Gadgets', sub: 'Curated operational widgets in the current layout' },
            { value: gadgetTypes.length || '—', label: 'Widget Types', sub: 'Available components in the workspace catalog' },
            { value: project ? projectDisplay : 'Program-only', label: 'Project Context', sub: project ? 'Explore-aware widgets follow the active project' : 'Select a project to unlock project-scoped insights' },
            { value: layoutId ? 'Saved' : 'Draft', label: 'Layout State', sub: layoutId ? 'Persisted program layout' : 'Using default starter arrangement' },
        ];

        return WorkspaceUI.shell({
            current: 'dashboard',
            testId: 'workspace-dashboard-page',
            eyebrow: 'Workspace',
            title: 'Dashboard',
            subtitle: 'Operational cockpit for daily delivery decisions, exception handling, and cross-module follow-up.',
            breadcrumbs: [{ label: 'Programs', onclick: 'App.navigate("programs")' }, { label: 'Dashboard' }],
            context: {
                program: prog.name,
                project: projectDisplay,
                status: prog.status || 'active',
                phase: project ? 'Project scoped' : 'Program scoped',
            },
            actionsHtml: `
                <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="DashboardView.saveLayout()">Save Layout</button>
                <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="DashboardView.openAddGadget()">Add Gadget</button>
            `,
            spotlights,
            bodyHtml,
        });
    }

    function _renderWorkspaceBody(project) {
        const projectDisplay = _projectDisplay(project);
        return `
            <div class="workspace-grid-shell">
                <section class="workspace-panel" data-testid="workspace-dashboard-focus">
                    <div class="workspace-panel__eyebrow">Operational Focus</div>
                    <h2 class="workspace-panel__title">Keep the highest-signal queues in view</h2>
                    <p class="workspace-panel__text">
                        The dashboard is the daily workspace for execution teams. Use it to keep defects, test momentum,
                        backlog handoffs, and cross-phase attention items visible without opening multiple modules.
                    </p>
                    <div class="workspace-link-list">
                        <button type="button" class="workspace-link-list__item" onclick="App.navigate('explore-outcomes')">
                            <span class="workspace-link-list__meta">
                                <span class="workspace-link-list__title">Explore Outcomes</span>
                                <span class="workspace-link-list__sub">Requirements, open items, and handoff readiness</span>
                            </span>
                            <span aria-hidden="true">→</span>
                        </button>
                        <button type="button" class="workspace-link-list__item" onclick="App.navigate('test-overview')">
                            <span class="workspace-link-list__meta">
                                <span class="workspace-link-list__title">Test Overview</span>
                                <span class="workspace-link-list__sub">Execution, retest, and sign-off coverage</span>
                            </span>
                            <span aria-hidden="true">→</span>
                        </button>
                        <button type="button" class="workspace-link-list__item" onclick="App.navigate('raid')">
                            <span class="workspace-link-list__meta">
                                <span class="workspace-link-list__title">RAID</span>
                                <span class="workspace-link-list__sub">Open risks, issues, actions, and decisions</span>
                            </span>
                            <span aria-hidden="true">→</span>
                        </button>
                    </div>
                </section>
                <section class="workspace-panel">
                    <div class="workspace-panel__eyebrow">Workspace Rules</div>
                    <h2 class="workspace-panel__title">How this layout behaves</h2>
                    <p class="workspace-panel__text">
                        Gadget layouts stay lightweight in this phase. The active program defines the primary data scope,
                        while the selected project${project ? ` (${esc(projectDisplay)})` : ''} sharpens Explore-linked counters and health cards.
                    </p>
                    <p class="workspace-panel__text">
                        Add or remove widgets, then save once the composition reflects the operating rhythm of the team.
                    </p>
                </section>
            </div>
            <div id="dashboardGrid" class="f5-dashboard-grid" data-testid="workspace-dashboard-grid">
                <div class="dashboard-gadget-loading dashboard-gadget-loading--wide">Loading workspace dashboard…</div>
            </div>
        `;
    }

    async function render() {
        _destroyCharts();
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        const project = typeof App.getActiveProject === 'function' ? App.getActiveProject() : null;

        if (!prog) {
            main.innerHTML = PGEmptyState.html({
                icon: 'dashboard',
                title: 'No Program Selected',
                description: 'Select a program to configure your dashboard.',
                action: { label: 'Go to Programs', onclick: "App.navigate('programs')" },
            });
            return;
        }

        main.innerHTML = _renderShell(
            prog,
            project,
            '<div class="workspace-loading">Loading dashboard workspace…</div>',
            {
                spotlights: [
                    { value: '—', label: 'Active Gadgets', sub: 'Loading saved layout' },
                    { value: '—', label: 'Widget Types', sub: 'Loading widget registry' },
                    { value: project ? _projectDisplay(project) : 'Program-only', label: 'Project Context', sub: project ? 'Project-specific explore metrics will be used' : 'Select a project to unlock project-scoped counters' },
                    { value: 'Loading', label: 'Layout State', sub: 'Resolving saved workspace layout' },
                ],
            },
        );

        try {
            const [typesResp, layoutResp] = await Promise.all([
                API.get('/reports/gadgets/types'),
                API.get(`/reports/dashboards?program_id=${prog.id}`),
            ]);

            gadgetTypes = typesResp.gadgets || [];

            const dashboards = layoutResp.dashboards || [];
            if (dashboards.length > 0) {
                layoutId = dashboards[0].id;
                gadgets = dashboards[0].layout || [];
            } else {
                layoutId = null;
                gadgets = _defaultGadgets();
            }

            main.innerHTML = _renderShell(prog, project, _renderWorkspaceBody(project));
            await renderGadgets(prog.id, project ? project.id : null);
        } catch (err) {
            main.innerHTML = _renderShell(prog, project, PGEmptyState.html({
                icon: 'warning',
                title: 'Workspace unavailable',
                description: esc(err.message || 'Unknown error'),
            }));
        }
    }

    async function renderGadgets(pid, projectId = null) {
        const grid = document.getElementById('dashboardGrid');
        if (!grid) return;
        grid.innerHTML = '';

        if (gadgets.length === 0) {
            grid.innerHTML = `
                <div class="dashboard-empty-state">
                    <div>
                        <strong>Empty dashboard</strong>
                        <div>Use Add Gadget to compose the workspace for your team.</div>
                    </div>
                </div>
            `;
            return;
        }

        for (let i = 0; i < gadgets.length; i += 1) {
            const gadget = gadgets[i];
            const containerId = `gadget-${i}`;
            const card = document.createElement('div');
            card.className = `card f5-gadget ${_sizeToClass(gadget.size || '1x1')}`;
            card.id = containerId;
            card.innerHTML = `
                <div class="f5-gadget-header">
                    <span class="f5-gadget-title">${esc(_labelForType(gadget.type))}</span>
                    <button class="f5-gadget-remove" onclick="DashboardView.removeGadget(${i})" title="Remove">×</button>
                </div>
                <div class="f5-gadget-body" id="${containerId}-body">
                    <div class="dashboard-gadget-loading">Loading widget…</div>
                </div>
            `;
            grid.appendChild(card);
        }

        try {
            const payload = await _loadBatchData(pid, projectId);
            const items = payload.items || {};
            const errors = payload.errors || {};

            for (let i = 0; i < gadgets.length; i += 1) {
                const body = document.getElementById(`gadget-${i}-body`);
                if (!body) continue;
                const type = gadgets[i].type;
                if (items[type]) {
                    _renderGadgetContent(body, items[type], i);
                } else {
                    body.innerHTML = `<div class="dashboard-gadget-error">${esc(errors[type] || 'Widget data unavailable')}</div>`;
                }
            }
        } catch (err) {
            grid.innerHTML = `<div class="dashboard-gadget-error dashboard-gadget-loading--wide">${esc(err.message || 'Unable to load widgets')}</div>`;
        }
    }

    async function _loadBatchData(pid, projectId = null) {
        const uniqueTypes = [...new Set(gadgets.map((g) => g.type))];
        const params = new URLSearchParams();
        params.set('types', uniqueTypes.join(','));
        if (projectId) params.set('project_id', String(projectId));
        return API.get(`/reports/gadgets/batch/${pid}?${params.toString()}`);
    }

    function _renderGadgetContent(body, gadgetData, idx) {
        const type = gadgetData.type;
        const data = gadgetData.data || {};

        if (type === 'gauge') {
            const value = data.value || 0;
            const colors = (gadgetData.chart_config || {}).colors || ['#ef4444', '#f59e0b', '#22c55e'];
            const thresholds = data.thresholds || [50, 70, 90];
            const color = value >= thresholds[2] ? colors[2] : value >= thresholds[1] ? colors[1] : colors[0];
            const extra = data.extra || {};
            const extraHtml = extra.requirements != null
                ? `<div class="dashboard-gauge__meta">${extra.requirements} requirements · ${Math.round(extra.test_coverage || 0)}% test coverage</div>`
                : '';

            body.innerHTML = `
                <div class="dashboard-gauge" style="--dashboard-gauge-color:${color}">
                    <div class="dashboard-gauge__value">${value}${data.max ? '%' : ''}</div>
                    <div class="dashboard-gauge__title">${esc(gadgetData.title || '')}</div>
                    ${extraHtml}
                </div>
            `;
            return;
        }

        if (type === 'kpi_strip') {
            const items = data.items || [];
            body.innerHTML = `
                <div class="dashboard-kpi-grid" style="--dashboard-kpi-columns:${Math.min(items.length || 1, 5)}">
                    ${items.map((item) => `
                        <button class="pg-kpi-card" onclick="App.navigate('${item.view}')" type="button">
                            <div class="pg-kpi-card__value">${esc(String(item.value ?? '–'))}</div>
                            <div class="pg-kpi-card__label">${esc(item.label)}</div>
                        </button>
                    `).join('')}
                </div>
            `;
            return;
        }

        if (type === 'action_list') {
            const actions = data.actions || [];
            if (!actions.length) {
                body.innerHTML = '<div class="dashboard-gadget-loading">No pending actions</div>';
                return;
            }

            body.innerHTML = `
                <div class="dashboard-action-list">
                    ${actions.slice(0, 5).map((action) => `
                        <button type="button" class="dashboard-action-row" onclick="App.navigate('${action.view}')">
                            <span class="dashboard-action-row__dot dashboard-action-row__dot--${esc(action.severity || 'neutral')}"></span>
                            <span class="dashboard-action-row__message">${esc(action.message)}</span>
                            <span class="dashboard-action-row__arrow" aria-hidden="true">→</span>
                        </button>
                    `).join('')}
                </div>
            `;
            return;
        }

        if (type === 'donut') {
            const canvasId = `gadgetChart-${idx}`;
            body.innerHTML = `<div class="dashboard-chart-shell"><canvas id="${canvasId}"></canvas></div>`;
            if (typeof Chart === 'undefined') return;
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;
            const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6'];
            const chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        data: data.values || [],
                        backgroundColor: (gadgetData.chart_config || {}).colors || colors,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } },
                    },
                },
            });
            chartInstances.push(chart);
            return;
        }

        if (type === 'line' || type === 'bar') {
            const canvasId = `gadgetChart-${idx}`;
            body.innerHTML = `<div class="dashboard-chart-shell"><canvas id="${canvasId}"></canvas></div>`;
            if (typeof Chart === 'undefined') return;
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;
            const colors = ['#0070f3', '#22c55e', '#f59e0b', '#ef4444'];
            const datasets = (data.datasets || []).map((dataset, i) => ({
                label: dataset.label || '',
                data: dataset.data || [],
                backgroundColor: dataset.color || colors[i % colors.length],
                borderColor: dataset.color || colors[i % colors.length],
                fill: false,
            }));
            const chart = new Chart(ctx, {
                type,
                data: { labels: data.labels || [], datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } },
                    plugins: { legend: { labels: { boxWidth: 10, font: { size: 11 } } } },
                },
            });
            chartInstances.push(chart);
            return;
        }

        if (type === 'table') {
            const columns = data.columns || [];
            const rows = data.rows || [];
            body.innerHTML = `
                <div class="dashboard-table-shell">
                    <table class="data-table">
                        <thead><tr>${columns.map((column) => `<th>${esc(column)}</th>`).join('')}</tr></thead>
                        <tbody>${rows.slice(0, 20).map((row) => `<tr>${columns.map((column) => `<td>${esc(String(row[column] ?? ''))}</td>`).join('')}</tr>`).join('')}</tbody>
                    </table>
                </div>
            `;
            return;
        }

        if (type === 'heatmap') {
            const items = data.items || data.matrix || [];
            if (Array.isArray(items) && items.length > 0 && items[0].module) {
                body.innerHTML = `
                    <div class="dashboard-table-shell">
                        <table class="data-table">
                            <thead><tr><th>Module</th><th>TCs</th><th>Defects</th><th>Pass Rate</th><th>Risk</th></tr></thead>
                            <tbody>${items.map((row) => {
                                return `<tr>
                                    <td>${esc(row.module)}</td>
                                    <td>${row.tc_count || 0}</td>
                                    <td>${row.defect_count || 0}</td>
                                    <td>${row.pass_rate || 0}%</td>
                                    <td><span class="dashboard-risk dashboard-risk--${esc(row.risk || 'low')}">${esc(row.risk || '?')}</span></td>
                                </tr>`;
                            }).join('')}</tbody>
                        </table>
                    </div>
                `;
            } else {
                body.innerHTML = '<div class="dashboard-gadget-loading">No heatmap data</div>';
            }
            return;
        }

        body.innerHTML = `<pre class="dashboard-json-fallback">${esc(JSON.stringify(data, null, 2))}</pre>`;
    }

    function _sizeToClass(size) {
        const map = {
            '1x1': 'f5-gadget-1x1',
            '2x1': 'f5-gadget-2x1',
            '2x2': 'f5-gadget-2x2',
        };
        return map[size] || 'f5-gadget-1x1';
    }

    function _labelForType(type) {
        const gadgetType = gadgetTypes.find((item) => item.type === type);
        return gadgetType ? gadgetType.label : type;
    }

    function openAddGadget() {
        const modalHtml = `
            <div class="modal-header">
                <h3>Add Gadget</h3>
                <button class="modal-close" onclick="DashboardView.closeAddGadget()" title="Close">×</button>
            </div>
            <div class="modal-body">
                <div class="dashboard-gadget-type-list">
                    ${gadgetTypes.map((gadgetType) => `
                        <button class="dashboard-gadget-type-btn" type="button" onclick="DashboardView.addGadget('${gadgetType.type}', '${gadgetType.default_size}')">
                            <strong>${esc(gadgetType.label)}</strong>
                            <span class="dashboard-gadget-type-btn__meta">Default size: ${esc(gadgetType.default_size)}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
        App.openModal(modalHtml);
    }

    function closeAddGadget() {
        App.closeModal();
    }

    function addGadget(type, size) {
        gadgets.push({ type, size });
        closeAddGadget();
        const prog = App.getActiveProgram();
        const project = typeof App.getActiveProject === 'function' ? App.getActiveProject() : null;
        if (prog) {
            document.getElementById('mainContent').innerHTML = _renderShell(prog, project, _renderWorkspaceBody(project));
            renderGadgets(prog.id, project ? project.id : null);
        }
    }

    function removeGadget(idx) {
        gadgets.splice(idx, 1);
        _destroyCharts();
        const prog = App.getActiveProgram();
        const project = typeof App.getActiveProject === 'function' ? App.getActiveProject() : null;
        if (prog) {
            document.getElementById('mainContent').innerHTML = _renderShell(prog, project, _renderWorkspaceBody(project));
            renderGadgets(prog.id, project ? project.id : null);
        }
    }

    async function saveLayout() {
        const prog = App.getActiveProgram();
        if (!prog) return;
        try {
            if (layoutId) {
                await API.put(`/reports/dashboards/${layoutId}`, { layout: gadgets });
            } else {
                const response = await API.post('/reports/dashboards', {
                    program_id: prog.id,
                    layout: gadgets,
                });
                layoutId = response.id;
            }
            if (typeof App !== 'undefined' && typeof App.toast === 'function') {
                App.toast('Dashboard layout saved', 'success');
            }
        } catch (err) {
            if (typeof App !== 'undefined' && typeof App.toast === 'function') {
                App.toast(`Error saving layout: ${err.message || 'Unknown error'}`, 'error');
            }
        }
    }

    return {
        render,
        openAddGadget,
        closeAddGadget,
        addGadget,
        removeGadget,
        saveLayout,
    };
})();
