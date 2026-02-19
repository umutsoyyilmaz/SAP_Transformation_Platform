/**
 * F5 — Dashboard View
 * Configurable gadget-grid dashboard with 12 built-in widget types.
 * Users can add/remove gadgets and save layout per program.
 */
const DashboardView = (() => {
    let gadgets = [];
    let gadgetTypes = [];
    let layoutId = null;
    let chartInstances = [];

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    function _destroyCharts() {
        chartInstances.forEach(c => { try { c.destroy(); } catch(_){} });
        chartInstances = [];
    }

    async function render() {
        _destroyCharts();
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();

        if (!prog) {
            main.innerHTML = `
                <div class="page-header"><h1>Dashboard</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">📊</div>
                    <div class="empty-state__title">No Program Selected</div>
                    <p>Select a program to configure your dashboard.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>Dashboard — ${esc(prog.name)}</h1>
                <div>
                    <button class="btn btn-primary" onclick="DashboardView.openAddGadget()">+ Add Gadget</button>
                    <button class="btn btn-secondary" onclick="DashboardView.saveLayout()">💾 Save Layout</button>
                </div>
            </div>
            <div id="dashboardGrid" class="f5-dashboard-grid">
                <div style="text-align:center;padding:40px;color:#666">Loading dashboard...</div>
            </div>
            <!-- Add Gadget Modal -->
            <div id="addGadgetModal" class="modal-overlay" style="display:none">
                <div class="modal" style="max-width:480px">
                    <div class="modal-header">
                        <h3>Add Gadget</h3>
                        <button class="modal-close" onclick="DashboardView.closeAddGadget()">&times;</button>
                    </div>
                    <div class="modal-body" id="gadgetTypeList"></div>
                </div>
            </div>`;

        try {
            // Load gadget types
            const typesResp = await API.get('/reports/gadgets/types');
            gadgetTypes = typesResp.gadgets || [];

            // Load saved layout
            const layoutResp = await API.get(`/reports/dashboards?program_id=${prog.id}`);
            const dashboards = layoutResp.dashboards || [];
            if (dashboards.length > 0) {
                layoutId = dashboards[0].id;
                gadgets = dashboards[0].layout || [];
            } else {
                // Default gadgets
                gadgets = [
                    { type: 'pass_rate_gauge', size: '1x1' },
                    { type: 'execution_trend', size: '2x1' },
                    { type: 'defect_by_severity', size: '1x1' },
                    { type: 'open_vs_closed', size: '1x1' },
                    { type: 'cycle_progress', size: '2x1' },
                    { type: 'recent_activity', size: '2x1' },
                ];
            }

            await renderGadgets(prog.id);
        } catch (err) {
            document.getElementById('dashboardGrid').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">⚠️</div>
                    <div class="empty-state__title">Error</div>
                    <p>${esc(err.message || 'Unknown error')}</p>
                </div>`;
        }
    }

    async function renderGadgets(pid) {
        const grid = document.getElementById('dashboardGrid');
        grid.innerHTML = '';

        if (gadgets.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column:1/-1">
                    <div class="empty-state__icon">📊</div>
                    <div class="empty-state__title">Empty Dashboard</div>
                    <p>Click "Add Gadget" to customize your dashboard.</p>
                </div>`;
            return;
        }

        for (let i = 0; i < gadgets.length; i++) {
            const g = gadgets[i];
            const sizeClass = _sizeToClass(g.size || '1x1');
            const containerId = `gadget-${i}`;
            const card = document.createElement('div');
            card.className = `card f5-gadget ${sizeClass}`;
            card.id = containerId;
            card.innerHTML = `
                <div class="f5-gadget-header">
                    <span class="f5-gadget-title">${esc(_labelForType(g.type))}</span>
                    <button class="f5-gadget-remove" onclick="DashboardView.removeGadget(${i})" title="Remove">&times;</button>
                </div>
                <div class="f5-gadget-body" id="${containerId}-body">
                    <div style="text-align:center;padding:20px;color:#999;font-size:13px">Loading...</div>
                </div>`;
            grid.appendChild(card);
        }

        // Load data for each gadget
        for (let i = 0; i < gadgets.length; i++) {
            _loadGadgetData(i, gadgets[i].type, pid);
        }
    }

    async function _loadGadgetData(idx, type, pid) {
        const body = document.getElementById(`gadget-${idx}-body`);
        if (!body) return;
        try {
            const data = await API.get(`/reports/gadgets/${type}/${pid}`);
            _renderGadgetContent(body, data, idx);
        } catch (err) {
            body.innerHTML = `<div style="color:#E74C3C;font-size:13px;padding:8px">${esc(err.message)}</div>`;
        }
    }

    function _renderGadgetContent(body, gadgetData, idx) {
        const type = gadgetData.type;
        const data = gadgetData.data;

        if (type === 'gauge') {
            const val = data.value || 0;
            const color = val >= 90 ? '#22c55e' : val >= 70 ? '#f59e0b' : '#ef4444';
            body.innerHTML = `
                <div style="text-align:center;padding:16px">
                    <div style="font-size:48px;font-weight:700;color:${color}">${val}%</div>
                    <div style="font-size:13px;color:#666;margin-top:4px">${esc(gadgetData.title || '')}</div>
                </div>`;
            return;
        }

        if (type === 'donut') {
            const canvasId = `gadgetChart-${idx}`;
            body.innerHTML = `<div style="position:relative;height:180px"><canvas id="${canvasId}"></canvas></div>`;
            if (typeof Chart === 'undefined') return;
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;
            const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6'];
            const chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels || [],
                    datasets: [{ data: data.values || [], backgroundColor: (gadgetData.chart_config || {}).colors || colors }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } } } },
            });
            chartInstances.push(chart);
            return;
        }

        if (type === 'line' || type === 'bar') {
            const canvasId = `gadgetChart-${idx}`;
            body.innerHTML = `<div style="position:relative;height:180px"><canvas id="${canvasId}"></canvas></div>`;
            if (typeof Chart === 'undefined') return;
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;
            const colors = ['#0070f3', '#22c55e', '#f59e0b', '#ef4444'];
            const datasets = (data.datasets || []).map((ds, i) => ({
                label: ds.label || '',
                data: ds.data || [],
                backgroundColor: ds.color || colors[i % colors.length],
                borderColor: ds.color || colors[i % colors.length],
                fill: false,
            }));
            const chart = new Chart(ctx, {
                type: type,
                data: { labels: data.labels || [], datasets },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } }, plugins: { legend: { labels: { boxWidth: 10, font: { size: 11 } } } } },
            });
            chartInstances.push(chart);
            return;
        }

        if (type === 'table') {
            const columns = data.columns || [];
            const rows = data.rows || [];
            body.innerHTML = `
                <div style="overflow-x:auto;max-height:200px;overflow-y:auto">
                    <table class="data-table" style="font-size:12px">
                        <thead><tr>${columns.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
                        <tbody>${rows.slice(0, 20).map(r => `<tr>${columns.map(c => `<td>${esc(String(r[c] ?? ''))}</td>`).join('')}</tr>`).join('')}</tbody>
                    </table>
                </div>`;
            return;
        }

        if (type === 'heatmap') {
            // Render as colored table
            const items = data.items || data.matrix || [];
            if (Array.isArray(items) && items.length > 0 && items[0].module) {
                body.innerHTML = `
                    <div style="overflow-x:auto;max-height:200px;overflow-y:auto">
                        <table class="data-table" style="font-size:12px">
                            <thead><tr><th>Module</th><th>TCs</th><th>Defects</th><th>Pass Rate</th><th>Risk</th></tr></thead>
                            <tbody>${items.map(r => {
                                const riskColor = r.risk === 'high' ? '#ef4444' : r.risk === 'medium' ? '#f59e0b' : '#22c55e';
                                return `<tr>
                                    <td>${esc(r.module)}</td>
                                    <td>${r.tc_count || 0}</td>
                                    <td>${r.defect_count || 0}</td>
                                    <td>${r.pass_rate || 0}%</td>
                                    <td><span style="color:${riskColor};font-weight:600">${r.risk || '?'}</span></td>
                                </tr>`;
                            }).join('')}</tbody>
                        </table>
                    </div>`;
            } else {
                body.innerHTML = `<div style="padding:8px;color:#999;font-size:13px">No heatmap data</div>`;
            }
            return;
        }

        // Fallback
        body.innerHTML = `<pre style="font-size:11px;max-height:180px;overflow:auto">${esc(JSON.stringify(data, null, 2))}</pre>`;
    }

    function _sizeToClass(size) {
        const map = { '1x1': 'f5-gadget-1x1', '2x1': 'f5-gadget-2x1', '2x2': 'f5-gadget-2x2' };
        return map[size] || 'f5-gadget-1x1';
    }

    function _labelForType(type) {
        const gt = gadgetTypes.find(g => g.type === type);
        return gt ? gt.label : type;
    }

    function openAddGadget() {
        const list = document.getElementById('gadgetTypeList');
        list.innerHTML = gadgetTypes.map(g => `
            <button class="f5-gadget-type-btn" onclick="DashboardView.addGadget('${g.type}', '${g.default_size}')">
                <strong>${esc(g.label)}</strong>
                <span style="font-size:12px;color:#999">Size: ${g.default_size}</span>
            </button>
        `).join('');
        document.getElementById('addGadgetModal').style.display = 'flex';
    }

    function closeAddGadget() {
        document.getElementById('addGadgetModal').style.display = 'none';
    }

    function addGadget(type, size) {
        gadgets.push({ type, size });
        closeAddGadget();
        const prog = App.getActiveProgram();
        if (prog) renderGadgets(prog.id);
    }

    function removeGadget(idx) {
        gadgets.splice(idx, 1);
        _destroyCharts();
        const prog = App.getActiveProgram();
        if (prog) renderGadgets(prog.id);
    }

    async function saveLayout() {
        const prog = App.getActiveProgram();
        if (!prog) return;
        try {
            if (layoutId) {
                await API.put(`/reports/dashboards/${layoutId}`, { layout: gadgets });
            } else {
                const resp = await API.post('/reports/dashboards', { program_id: prog.id, layout: gadgets });
                layoutId = resp.id;
            }
            if (typeof App !== 'undefined' && App.showToast) App.showToast('Dashboard layout saved', 'success');
        } catch (err) {
            alert('Error saving layout: ' + (err.message || 'Unknown'));
        }
    }

    return { render, openAddGadget, closeAddGadget, addGadget, removeGadget, saveLayout };
})();
