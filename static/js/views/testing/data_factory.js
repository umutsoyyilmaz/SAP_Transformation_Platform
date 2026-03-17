/**
 * SAP Transformation Platform — Data Factory View (Sprint 10)
 *
 * 5-tab layout:
 *   1. Data Objects   — master list + CRUD + quality badges
 *   2. Migration Waves — wave timeline + progress
 *   3. Cleansing      — tasks per object, run simulation
 *   4. Load Cycles    — ETL executions + reconciliation
 *   5. Dashboard      — quality score + environment comparison charts
 */
const DataFactoryView = (() => {
    let _pid = null;
    let _objects = [];
    let _waves = [];
    let _currentTab = 'objects';
    let _selectedObjectId = null;

    // ── Filter state ──────────────────────────────────────────────────
    let _objSearch = '';
    let _objFilters = {};

    const RULE_ICONS = {
        not_null: '🔒', unique: '🔑', range: '📏', regex: '🔤', lookup: '🔍', custom: '⚙️',
    };

    function _badge(status) {
        return PGStatusRegistry.badge(status, { label: fmtStatus(status) });
    }

    function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
    function fmtNum(n) { return (n ?? 0).toLocaleString('en-US'); }
    function fmtPct(n) { return n != null ? n.toFixed(1) + '%' : '—'; }
    function fmtDate(d) { return d ? new Date(d).toLocaleDateString('en-US') : '—'; }
    function fmtStatus(s) { return (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
    function qualityClass(score) {
        if (score == null) return 'badge-secondary';
        if (score >= 90) return 'badge-success';
        if (score >= 75) return 'badge-warning';
        return 'badge-danger';
    }
    function _deliveryNav(hub, current) {
        return typeof DeliveryHubUI !== 'undefined' && DeliveryHubUI?.nav
            ? DeliveryHubUI.nav(hub, current)
            : '';
    }

    // ══════════════════════════════════════════════════════════════════════
    // MAIN RENDER
    // ══════════════════════════════════════════════════════════════════════
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        _pid = prog ? prog.id : null;

        if (!_pid) {
            main.innerHTML = PGEmptyState.html({ icon: 'data', title: 'Data Factory', description: 'Select a program to access the Data Factory.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Data Factory' }])}
                <div class="data-factory-header">
                    <h2 class="pg-view-title">Data Factory</h2>
                    <div class="data-factory-header__actions">
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="DataFactoryView.showAIMigrationModal()">AI Migration</button>
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="DataFactoryView.showAIQualityModal()">AI Quality</button>
                        <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="DataFactoryView.showCreateWave()">+ New Wave</button>
                        <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="DataFactoryView.showCreateObject()">+ New Data Object</button>
                    </div>
                </div>
            </div>
            ${typeof DeliveryHubUI !== 'undefined' && DeliveryHubUI?.nav
                ? DeliveryHubUI.nav('build', 'data-factory')
                : _deliveryNav('build', 'data-factory')}
            <div class="tabs data-factory-tabs" id="dfTabs">
                <button class="tab active" data-tab="objects" onclick="DataFactoryView.switchTab('objects')">Data Objects</button>
                <button class="tab" data-tab="waves" onclick="DataFactoryView.switchTab('waves')">Migration Waves</button>
                <button class="tab" data-tab="cleansing" onclick="DataFactoryView.switchTab('cleansing')">Cleansing</button>
                <button class="tab" data-tab="loads" onclick="DataFactoryView.switchTab('loads')">Load Cycles</button>
                <button class="tab" data-tab="dashboard" onclick="DataFactoryView.switchTab('dashboard')">Dashboard</button>
            </div>
            <div id="dfContent"><div class="data-factory-loading"><div class="spinner"></div></div></div>
        `;

        await loadAll();
    }

    async function loadAll() {
        try {
            const [objRes, waveRes] = await Promise.all([
                API.get(`/data-factory/objects?program_id=${_pid}`),
                API.get(`/data-factory/waves?program_id=${_pid}`),
            ]);
            _objects = objRes.items || objRes || [];
            _waves = waveRes.items || waveRes || [];
            renderTab();
        } catch (e) {
            document.getElementById('dfContent').innerHTML =
                `<div class="empty-state"><p>⚠️ ${esc(e.message)}</p></div>`;
        }
    }

    function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('#dfTabs .tab').forEach(t =>
            t.classList.toggle('active', t.dataset.tab === tab));
        renderTab();
    }

    function renderTab() {
        switch (_currentTab) {
            case 'objects': renderObjects(); break;
            case 'waves': renderWaves(); break;
            case 'cleansing': renderCleansing(); break;
            case 'loads': renderLoads(); break;
            case 'dashboard': renderDashboard(); break;
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 1: DATA OBJECTS
    // ══════════════════════════════════════════════════════════════════════
    function renderObjects() {
        const c = document.getElementById('dfContent');
        if (!_objects.length) {
            c.innerHTML = PGEmptyState.html({ icon: 'data', title: 'No data objects yet', description: 'Create your first data object to start the migration lifecycle.', action: { label: '+ New Data Object', onclick: 'DataFactoryView.showCreateObject()' } });
            return;
        }

        // Summary cards
        const total = _objects.length;
        const avgQ = _objects.filter(o => o.quality_score != null);
        const avgScore = avgQ.length ? (avgQ.reduce((s, o) => s + o.quality_score, 0) / avgQ.length).toFixed(1) : '—';
        const totalRecs = _objects.reduce((s, o) => s + (o.record_count || 0), 0);
        const readyCount = _objects.filter(o => ['ready', 'migrated'].includes(o.status)).length;

        c.innerHTML = `
            <div class="data-factory-kpi-grid">
                <div class="data-factory-kpi-card">
                    <div class="data-factory-kpi-card__label">Data Objects</div>
                    <div class="data-factory-kpi-card__value">${total}</div>
                </div>
                <div class="data-factory-kpi-card">
                    <div class="data-factory-kpi-card__label">Avg Quality</div>
                    <div class="data-factory-kpi-card__value ${parseFloat(avgScore) >= 85 ? 'data-factory-kpi-card__value--positive' : 'data-factory-kpi-card__value--warning'}">${avgScore}%</div>
                </div>
                <div class="data-factory-kpi-card">
                    <div class="data-factory-kpi-card__label">Total Records</div>
                    <div class="data-factory-kpi-card__value">${fmtNum(totalRecs)}</div>
                </div>
                <div class="data-factory-kpi-card">
                    <div class="data-factory-kpi-card__label">Ready / Migrated</div>
                    <div class="data-factory-kpi-card__value data-factory-kpi-card__value--positive">${readyCount} / ${total}</div>
                </div>
            </div>

            <div id="objFilterBar" class="data-factory-filter-bar"></div>
            <div id="objTableArea"></div>
        `;
        renderObjectFilterBar();
        applyObjectFilter();
    }

    function renderObjectFilterBar() {
        const el = document.getElementById('objFilterBar');
        if (!el) return;
        el.innerHTML = ExpUI.filterBar({
            id: 'objFB',
            searchPlaceholder: 'Search data objects…',
            searchValue: _objSearch,
            onSearch: 'DataFactoryView.setObjSearch(this.value)',
            onChange: 'DataFactoryView.onObjFilterChange',
            filters: [
                {
                    id: 'status', label: 'Status', type: 'multi', color: '#10b981',
                    options: ['draft','profiled','cleansed','ready','migrated','archived'].map(s => ({ value: s, label: fmtStatus(s) })),
                    selected: _objFilters.status || [],
                },
                {
                    id: 'source_system', label: 'Source', type: 'multi', color: '#3b82f6',
                    options: [...new Set(_objects.map(o => o.source_system).filter(Boolean))].sort().map(s => ({ value: s, label: s })),
                    selected: _objFilters.source_system || [],
                },
                {
                    id: 'owner', label: 'Owner', type: 'multi', color: '#8b5cf6',
                    options: [...new Set(_objects.map(o => o.owner).filter(Boolean))].sort().map(o => ({ value: o, label: o })),
                    selected: _objFilters.owner || [],
                },
            ],
            actionsHtml: `<span class="data-factory-filter-count" id="objItemCount"></span>`,
        });
    }

    function setObjSearch(val) {
        _objSearch = val;
        applyObjectFilter();
    }

    function onObjFilterChange(update) {
        if (update._clearAll) {
            _objFilters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete _objFilters[key];
                } else {
                    _objFilters[key] = val;
                }
            });
        }
        renderObjectFilterBar();
        applyObjectFilter();
    }

    function applyObjectFilter() {
        let filtered = [..._objects];

        if (_objSearch) {
            const q = _objSearch.toLowerCase();
            filtered = filtered.filter(o =>
                (o.name || '').toLowerCase().includes(q) ||
                (o.source_system || '').toLowerCase().includes(q) ||
                (o.target_table || '').toLowerCase().includes(q) ||
                (o.owner || '').toLowerCase().includes(q) ||
                (o.description || '').toLowerCase().includes(q)
            );
        }

        Object.entries(_objFilters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (values.length === 0) return;
            filtered = filtered.filter(o => values.includes(String(o[key])));
        });

        const countEl = document.getElementById('objItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${_objects.length}`;

        const tableEl = document.getElementById('objTableArea');
        if (!tableEl) return;
        if (filtered.length === 0) {
            tableEl.innerHTML = '<div class="empty-state data-factory-empty"><p>No data objects match your filters.</p></div>';
            return;
        }

        tableEl.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Source</th>
                        <th>Target Table</th>
                        <th>Records</th>
                        <th>Quality</th>
                        <th>Status</th>
                        <th>Owner</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${filtered.map(o => `
                        <tr onclick="DataFactoryView.showObjectDetail(${o.id})" class="clickable-row data-factory-row-clickable">
                            <td><strong>${esc(o.name)}</strong>
                                ${o.description ? `<br><small class="data-factory-cell-copy data-factory-cell-copy--small">${esc(o.description)}</small>` : ''}
                            </td>
                            <td><span class="badge badge-info">${esc(o.source_system)}</span></td>
                            <td><code class="data-factory-code">${esc(o.target_table || '—')}</code></td>
                            <td class="data-factory-table-cell--right">${fmtNum(o.record_count)}</td>
                            <td>
                                ${o.quality_score != null
                                    ? `<span class="badge ${qualityClass(o.quality_score)}">${o.quality_score.toFixed(1)}%</span>`
                                    : '<span class="badge badge-secondary">—</span>'}
                            </td>
                            <td>${_badge(o.status)}</td>
                            <td>${esc(o.owner || '—')}</td>
                            <td>
                                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();DataFactoryView.deleteObject(${o.id})">🗑️</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 2: MIGRATION WAVES
    // ══════════════════════════════════════════════════════════════════════
    function renderWaves() {
        const c = document.getElementById('dfContent');
        if (!_waves.length) {
            c.innerHTML = PGEmptyState.html({ icon: 'data', title: 'No migration waves defined', action: { label: '+ New Wave', onclick: 'DataFactoryView.showCreateWave()' } });
            return;
        }

        c.innerHTML = `
            <div class="data-factory-waves-grid">
                ${_waves.map(w => `
                    <div class="card data-factory-wave-card" onclick="DataFactoryView.showWaveDetail(${w.id})" style="--df-accent:${PGStatusRegistry.colors(w.status).fg}">
                        <div class="data-factory-wave-card__body">
                            <div class="data-factory-wave-card__header">
                                <h3 class="data-factory-wave-card__title">${esc(w.name)}</h3>
                                ${_badge(w.status)}
                            </div>
                            ${w.description ? `<p class="data-factory-wave-card__description">${esc(w.description)}</p>` : ''}
                            <div class="data-factory-wave-card__meta">
                                <div><strong>Planned:</strong> ${fmtDate(w.planned_start)} → ${fmtDate(w.planned_end)}</div>
                                <div><strong>Actual:</strong> ${fmtDate(w.actual_start)} → ${fmtDate(w.actual_end)}</div>
                            </div>
                            <div class="data-factory-wave-card__actions">
                                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();DataFactoryView.deleteWave(${w.id})">🗑️</button>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 3: CLEANSING
    // ══════════════════════════════════════════════════════════════════════
    async function renderCleansing() {
        const c = document.getElementById('dfContent');

        if (!_objects.length) {
            c.innerHTML = `<div class="empty-state"><p>No data objects. Create objects first.</p></div>`;
            return;
        }

        // Object selector + tasks
        const selId = _selectedObjectId || (_objects.length ? _objects[0].id : null);
        _selectedObjectId = selId;

        c.innerHTML = `
            <div class="data-factory-select-row">
                <label class="data-factory-select-row__label">Data Object:</label>
                <select id="dfCleansingObjSelect" class="form-control data-factory-select"
                        onchange="DataFactoryView.onCleansingObjectChange(this.value)">
                    ${_objects.map(o => `<option value="${o.id}" ${o.id === selId ? 'selected' : ''}>${esc(o.name)} (${esc(o.source_system)})</option>`).join('')}
                </select>
                <button class="btn btn-primary btn-sm" onclick="DataFactoryView.showCreateTask()">+ New Rule</button>
            </div>
            <div id="dfCleansingTasks"><div class="data-factory-spinner-shell"><div class="spinner"></div></div></div>
        `;

        await loadCleansingTasks(selId);
    }

    async function loadCleansingTasks(objId) {
        const tc = document.getElementById('dfCleansingTasks');
        try {
            const tasks = await API.get(`/data-factory/objects/${objId}/tasks`);
            const list = Array.isArray(tasks) ? tasks : (tasks.items || []);

            if (!list.length) {
                tc.innerHTML = `<div class="empty-state"><p>No cleansing rules for this object.</p></div>`;
                return;
            }

            const passed = list.filter(t => t.status === 'passed').length;
            const failed = list.filter(t => t.status === 'failed').length;
            const pending = list.filter(t => ['pending', 'running'].includes(t.status)).length;

            tc.innerHTML = `
                <div class="data-factory-summary-row">
                    <span class="badge badge-success">✓ ${passed} Passed</span>
                    <span class="badge badge-danger">✗ ${failed} Failed</span>
                    <span class="badge badge-secondary">⏳ ${pending} Pending</span>
                </div>
                <table class="data-table data-factory-table">
                    <thead>
                        <tr>
                            <th>Rule Type</th>
                            <th>Expression</th>
                            <th>Description</th>
                            <th>Pass</th>
                            <th>Fail</th>
                            <th>Status</th>
                            <th>Last Run</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${list.map(t => `
                            <tr>
                                <td>${RULE_ICONS[t.rule_type] || '⚙️'} <strong>${esc(t.rule_type)}</strong></td>
                                <td><code class="data-factory-code">${esc(t.rule_expression)}</code></td>
                                <td>${esc(t.description || '')}</td>
                                <td class="data-factory-table-cell--right data-factory-cell-copy data-factory-cell-copy--success">${t.pass_count != null ? fmtNum(t.pass_count) : '—'}</td>
                                <td class="data-factory-table-cell--right data-factory-cell-copy data-factory-cell-copy--danger">${t.fail_count != null ? fmtNum(t.fail_count) : '—'}</td>
                                <td><span class="badge badge-${t.status === 'passed' ? 'success' : t.status === 'failed' ? 'danger' : 'secondary'}">${fmtStatus(t.status)}</span></td>
                                <td>${fmtDate(t.last_run_at)}</td>
                                <td>
                                    <button class="btn btn-sm btn-primary" onclick="DataFactoryView.runTask(${t.id})" ${['running'].includes(t.status) ? 'disabled' : ''}>▶ Run</button>
                                    <button class="btn btn-sm btn-danger" onclick="DataFactoryView.deleteTask(${t.id})">🗑️</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (e) {
            tc.innerHTML = `<div class="empty-state"><p class="data-factory-empty-inline">⚠️ ${esc(e.message)}</p></div>`;
        }
    }

    function onCleansingObjectChange(val) {
        _selectedObjectId = parseInt(val, 10);
        loadCleansingTasks(_selectedObjectId);
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 4: LOAD CYCLES
    // ══════════════════════════════════════════════════════════════════════
    async function renderLoads() {
        const c = document.getElementById('dfContent');

        if (!_objects.length) {
            c.innerHTML = `<div class="empty-state"><p>No data objects. Create objects first.</p></div>`;
            return;
        }

        const selId = _selectedObjectId || (_objects.length ? _objects[0].id : null);
        _selectedObjectId = selId;

        c.innerHTML = `
            <div class="data-factory-select-row">
                <label class="data-factory-select-row__label">Data Object:</label>
                <select id="dfLoadObjSelect" class="form-control data-factory-select"
                        onchange="DataFactoryView.onLoadObjectChange(this.value)">
                    ${_objects.map(o => `<option value="${o.id}" ${o.id === selId ? 'selected' : ''}>${esc(o.name)} (${esc(o.source_system)})</option>`).join('')}
                </select>
                <button class="btn btn-primary btn-sm" onclick="DataFactoryView.showCreateLoad()">+ New Load Cycle</button>
            </div>
            <div id="dfLoadList"><div class="data-factory-spinner-shell"><div class="spinner"></div></div></div>
        `;

        await loadLoadCycles(selId);
    }

    async function loadLoadCycles(objId) {
        const lc = document.getElementById('dfLoadList');
        try {
            const cycles = await API.get(`/data-factory/objects/${objId}/loads`);
            const list = Array.isArray(cycles) ? cycles : (cycles.items || []);

            if (!list.length) {
                lc.innerHTML = `<div class="empty-state"><p>No load cycles for this object.</p></div>`;
                return;
            }

            lc.innerHTML = `
                <table class="data-table data-factory-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Environment</th>
                            <th>Load Type</th>
                            <th>Records Loaded</th>
                            <th>Records Failed</th>
                            <th>Status</th>
                            <th>Started</th>
                            <th>Completed</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${list.map(c => `
                            <tr>
                                <td><strong>#${c.id}</strong></td>
                                <td><span class="badge badge-info">${esc(c.environment)}</span></td>
                                <td>${esc(c.load_type)}</td>
                                <td class="data-factory-table-cell--right data-factory-cell-copy data-factory-cell-copy--success">${c.records_loaded != null ? fmtNum(c.records_loaded) : '—'}</td>
                                <td class="data-factory-table-cell--right data-factory-cell-copy data-factory-cell-copy--danger">${c.records_failed != null ? fmtNum(c.records_failed) : '—'}</td>
                                <td>${_badge(c.status)}</td>
                                <td>${fmtDate(c.started_at)}</td>
                                <td>${fmtDate(c.completed_at)}</td>
                                <td>
                                    <button class="btn btn-sm btn-secondary" onclick="DataFactoryView.showReconciliations(${c.id})">Recon</button>
                                    ${c.status === 'pending' ? `<button class="btn btn-sm btn-primary" onclick="DataFactoryView.startLoad(${c.id})">▶ Start</button>` : ''}
                                    ${c.status === 'running' ? `<button class="btn btn-sm btn-success" onclick="DataFactoryView.completeLoad(${c.id})">✓ Complete</button>` : ''}
                                </td>
                            </tr>
                            ${c.error_log ? `<tr><td colspan="9" class="data-factory-alert-row">⚠️ ${esc(c.error_log)}</td></tr>` : ''}
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (e) {
            lc.innerHTML = `<div class="empty-state"><p class="data-factory-empty-inline">⚠️ ${esc(e.message)}</p></div>`;
        }
    }

    function onLoadObjectChange(val) {
        _selectedObjectId = parseInt(val, 10);
        loadLoadCycles(_selectedObjectId);
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 5: DASHBOARD
    // ══════════════════════════════════════════════════════════════════════
    async function renderDashboard() {
        const c = document.getElementById('dfContent');
        c.innerHTML = `<div class="data-factory-loading"><div class="spinner"></div></div>`;

        try {
            const [qs, cc] = await Promise.all([
                API.get(`/data-factory/quality-score?program_id=${_pid}`),
                API.get(`/data-factory/cycle-comparison?program_id=${_pid}`),
            ]);

            const byStatus = qs.by_status || {};
            const envs = cc.environments || {};

            c.innerHTML = `
                <div class="data-factory-dashboard-grid">
                    <div class="card data-factory-dashboard-card">
                        <h3 class="data-factory-dashboard-card__title">Data Quality Overview</h3>
                        <p class="data-factory-dashboard-card__meta">${qs.total_objects} objects</p>
                        <div class="data-factory-quality-layout">
                            <div class="data-factory-quality-score">
                                <div class="data-factory-quality-score__value" style="--df-quality-color:${qs.avg_quality_score >= 85 ? 'var(--pg-color-positive)' : qs.avg_quality_score >= 70 ? 'var(--pg-color-warning)' : 'var(--pg-color-negative)'}">
                                    ${qs.avg_quality_score ? qs.avg_quality_score.toFixed(1) : '0'}%
                                </div>
                                <div class="data-factory-quality-score__label">Avg Quality Score</div>
                            </div>
                            <div class="data-factory-quality-chart-wrap">
                                <canvas id="dfQualityChart" height="180"></canvas>
                            </div>
                        </div>
                    </div>

                    <div class="card data-factory-dashboard-card">
                        <h3 class="data-factory-dashboard-card__title data-factory-dashboard-card__title--spaced">Object Status Breakdown</h3>
                        <div class="data-factory-status-grid">
                            ${Object.entries(byStatus).map(([s, cnt]) => `
                                <div class="data-factory-status-chip" style="--df-chip-bg:${PGStatusRegistry.colors(s).bg};--df-chip-fg:${PGStatusRegistry.colors(s).fg}">
                                    <div class="data-factory-status-chip__value">${cnt}</div>
                                    <div class="data-factory-status-chip__label">${fmtStatus(s)}</div>
                                </div>
                            `).join('')}
                        </div>
                        ${Object.keys(byStatus).length === 0 ? '<p class="data-factory-empty-copy">No data yet.</p>' : ''}
                    </div>
                </div>

                <div class="card data-factory-dashboard-card">
                    <h3 class="data-factory-dashboard-card__title data-factory-dashboard-card__title--spaced">Environment Load Comparison</h3>
                    ${Object.keys(envs).length === 0
                        ? '<p class="data-factory-empty-copy">No load cycles yet.</p>'
                        : `
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Environment</th>
                                    <th>Total Cycles</th>
                                    <th>Completed</th>
                                    <th>Failed</th>
                                    <th>Records Loaded</th>
                                    <th>Records Failed</th>
                                    <th>Success Rate</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${Object.entries(envs).map(([env, d]) => {
                                    const rate = d.total > 0 ? ((d.completed / d.total) * 100).toFixed(0) : '—';
                                    return `
                                    <tr>
                                        <td><span class="badge badge-info">${esc(env)}</span></td>
                                        <td class="data-factory-table-cell--right">${d.total}</td>
                                        <td class="data-factory-table-cell--right data-factory-cell-copy data-factory-cell-copy--success">${d.completed}</td>
                                        <td class="data-factory-table-cell--right data-factory-cell-copy data-factory-cell-copy--danger">${d.failed}</td>
                                        <td class="data-factory-table-cell--right">${fmtNum(d.records_loaded)}</td>
                                        <td class="data-factory-table-cell--right data-factory-cell-copy data-factory-cell-copy--danger">${fmtNum(d.records_failed)}</td>
                                        <td>
                                            <div class="data-factory-progress">
                                                <div class="data-factory-progress__track">
                                                    <div class="data-factory-progress__fill" style="--df-progress-pct:${rate}%;--df-progress-color:${parseInt(rate, 10) >= 80 ? 'var(--pg-color-positive)' : 'var(--pg-color-warning)'}"></div>
                                                </div>
                                                <span class="data-factory-progress__label">${rate}%</span>
                                            </div>
                                        </td>
                                    </tr>`;
                                }).join('')}
                            </tbody>
                        </table>
                        <div class="data-factory-chart-wrap"><canvas id="dfEnvChart" height="200"></canvas></div>
                        `
                    }
                </div>
            `;

            // Draw charts
            _drawQualityChart(qs.objects || []);
            _drawEnvChart(envs);
        } catch (e) {
            c.innerHTML = `<div class="empty-state"><p>⚠️ ${esc(e.message)}</p></div>`;
        }
    }

    function _drawQualityChart(objects) {
        const canvas = document.getElementById('dfQualityChart');
        if (!canvas || !objects.length) return;
        const ctx = canvas.getContext('2d');
        const labels = objects.map(o => o.name.length > 18 ? o.name.substring(0, 18) + '…' : o.name);
        const scores = objects.map(o => o.quality_score ?? 0);
        const colors = scores.map(s => s >= 90 ? '#30914c' : s >= 75 ? '#e76500' : '#bb0000');

        try {
            const chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [{
                        label: 'Quality Score',
                        data: scores,
                        backgroundColor: colors.map(c => c + '44'),
                        borderColor: colors,
                        borderWidth: 1,
                    }],
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { min: 0, max: 100, ticks: { callback: v => v + '%' } },
                    },
                },
            });
            if (typeof App !== 'undefined' && App._charts) App._charts.push(chart);
        } catch {}
    }

    function _drawEnvChart(envs) {
        const canvas = document.getElementById('dfEnvChart');
        if (!canvas || !Object.keys(envs).length) return;
        const ctx = canvas.getContext('2d');
        const labels = Object.keys(envs);
        const loaded = labels.map(e => envs[e].records_loaded || 0);
        const failed = labels.map(e => envs[e].records_failed || 0);

        try {
            const chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        { label: 'Records Loaded', data: loaded, backgroundColor: '#30914c88', borderColor: '#30914c', borderWidth: 1 },
                        { label: 'Records Failed', data: failed, backgroundColor: '#bb000088', borderColor: '#bb0000', borderWidth: 1 },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'top' } },
                    scales: {
                        y: { beginAtZero: true, ticks: { callback: v => v.toLocaleString() } },
                    },
                },
            });
            if (typeof App !== 'undefined' && App._charts) App._charts.push(chart);
        } catch {}
    }

    // ══════════════════════════════════════════════════════════════════════
    // MODALS — CREATE / DETAIL
    // ══════════════════════════════════════════════════════════════════════

    function _modal(title, body) {
        // Remove any leftover custom modal
        const existing = document.getElementById('dfModal');
        if (existing) existing.remove();

        // Use standard App.openModal system for consistency (ESC, backdrop-click, z-index)
        App.openModal(`
            <div class="modal-header">
                <h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal-body data-factory-modal-body">
                ${body}
            </div>
        `);
    }

    async function showCreateObject() {
        const members = await TeamMemberPicker.fetchMembers(_pid);
        const ownerHtml = TeamMemberPicker.renderSelect('df_obj_owner', members, '', { cssClass: 'form-control', placeholder: '— Select Owner —' });
        _modal('📦 New Data Object', `
            <form onsubmit="DataFactoryView.submitCreateObject(event)">
                <div class="data-factory-form-stack">
                    <div><label>Name *</label><input class="form-control" id="df_obj_name" required></div>
                    <div><label>Source System *</label><input class="form-control" id="df_obj_source" required placeholder="SAP ECC, Legacy HR, etc."></div>
                    <div><label>Target Table</label><input class="form-control" id="df_obj_target" placeholder="S/4HANA target table"></div>
                    <div><label>Record Count</label><input type="number" class="form-control" id="df_obj_records" value="0"></div>
                    <div><label>Owner</label>${ownerHtml}</div>
                    <div><label>Description</label><textarea class="form-control" id="df_obj_desc" rows="2"></textarea></div>
                </div>
                <div class="data-factory-modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create</button>
                </div>
            </form>
        `);
    }

    async function submitCreateObject(e) {
        e.preventDefault();
        try {
            await API.post('/data-factory/objects', {
                program_id: _pid,
                name: document.getElementById('df_obj_name').value,
                source_system: document.getElementById('df_obj_source').value,
                target_table: document.getElementById('df_obj_target').value || null,
                record_count: parseInt(document.getElementById('df_obj_records').value) || 0,
                owner: document.getElementById('df_obj_owner').value || null,
                owner_id: document.getElementById('df_obj_owner').value ? parseInt(document.getElementById('df_obj_owner').value) : null,
                description: document.getElementById('df_obj_desc').value || null,
            });
            App.closeModal();
            App.toast('Data object created', 'success');
            await loadAll();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    function showCreateWave() {
        _modal('🌊 New Migration Wave', `
            <form onsubmit="DataFactoryView.submitCreateWave(event)">
                <div class="data-factory-form-stack">
                    <div><label>Wave Number *</label><input type="number" class="form-control" id="df_wave_num" required min="1"></div>
                    <div><label>Name *</label><input class="form-control" id="df_wave_name" required></div>
                    <div><label>Description</label><textarea class="form-control" id="df_wave_desc" rows="2"></textarea></div>
                    <div class="data-factory-form-grid">
                        <div><label>Planned Start</label><input type="date" class="form-control" id="df_wave_start"></div>
                        <div><label>Planned End</label><input type="date" class="form-control" id="df_wave_end"></div>
                    </div>
                </div>
                <div class="data-factory-modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create</button>
                </div>
            </form>
        `);
    }

    async function submitCreateWave(e) {
        e.preventDefault();
        try {
            await API.post('/data-factory/waves', {
                program_id: _pid,
                wave_number: parseInt(document.getElementById('df_wave_num').value),
                name: document.getElementById('df_wave_name').value,
                description: document.getElementById('df_wave_desc').value || null,
                planned_start: document.getElementById('df_wave_start').value || null,
                planned_end: document.getElementById('df_wave_end').value || null,
            });
            App.closeModal();
            App.toast('Migration wave created', 'success');
            await loadAll();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function showObjectDetail(objId) {
        try {
            const obj = await API.get(`/data-factory/objects/${objId}`);
            _modal(`📦 ${esc(obj.name)}`, `
                <div class="data-factory-detail-grid">
                    <div><strong>Source:</strong> ${esc(obj.source_system)}</div>
                    <div><strong>Target:</strong> <code class="data-factory-code">${esc(obj.target_table || '—')}</code></div>
                    <div><strong>Records:</strong> ${fmtNum(obj.record_count)}</div>
                    <div><strong>Quality:</strong> ${obj.quality_score != null ? obj.quality_score.toFixed(1) + '%' : '—'}</div>
                    <div><strong>Status:</strong> ${_badge(obj.status)}</div>
                    <div><strong>Owner:</strong> ${esc(obj.owner || '—')}</div>
                </div>
                ${obj.description ? `<p class="data-factory-detail-copy">${esc(obj.description)}</p>` : ''}
                <div class="data-factory-meta-row">
                    <span>🧹 ${obj.task_count ?? 0} cleansing tasks</span>
                    <span>🔄 ${obj.load_count ?? 0} load cycles</span>
                </div>
                <div class="data-factory-status-section">
                    <label class="data-factory-status-section__label">Update Status:</label>
                    <div class="data-factory-status-section__actions">
                        ${['draft','profiled','cleansed','ready','migrated','archived'].map(s =>
                            `<button class="btn btn-sm ${s === obj.status ? 'btn-primary' : 'btn-secondary'}"
                                     onclick="DataFactoryView.updateObjectStatus(${obj.id},'${s}')">${fmtStatus(s)}</button>`
                        ).join('')}
                    </div>
                </div>
            `);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function updateObjectStatus(objId, status) {
        try {
            await API.put(`/data-factory/objects/${objId}`, { status });
            App.closeModal();
            App.toast('Status updated', 'success');
            await loadAll();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function showWaveDetail(waveId) {
        try {
            const wave = await API.get(`/data-factory/waves/${waveId}`);
            _modal(`🌊 ${esc(wave.name)}`, `
                <div class="data-factory-detail-grid">
                    <div><strong>Wave #:</strong> ${wave.wave_number}</div>
                    <div><strong>Status:</strong> ${_badge(wave.status)}</div>
                    <div><strong>Planned:</strong> ${fmtDate(wave.planned_start)} → ${fmtDate(wave.planned_end)}</div>
                    <div><strong>Actual:</strong> ${fmtDate(wave.actual_start)} → ${fmtDate(wave.actual_end)}</div>
                    <div><strong>Load Cycles:</strong> ${wave.load_cycle_count ?? 0}</div>
                    <div><strong>Records Loaded:</strong> ${fmtNum(wave.total_loaded)}</div>
                </div>
                ${wave.description ? `<p class="data-factory-detail-copy">${esc(wave.description)}</p>` : ''}
                <div class="data-factory-status-section">
                    <label class="data-factory-status-section__label">Update Status:</label>
                    <div class="data-factory-status-section__actions">
                        ${['planned','in_progress','completed','cancelled'].map(s =>
                            `<button class="btn btn-sm ${s === wave.status ? 'btn-primary' : 'btn-secondary'}"
                                     onclick="DataFactoryView.updateWaveStatus(${wave.id},'${s}')">${fmtStatus(s)}</button>`
                        ).join('')}
                    </div>
                </div>
            `);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function updateWaveStatus(waveId, status) {
        try {
            await API.put(`/data-factory/waves/${waveId}`, { status });
            App.closeModal();
            App.toast('Wave status updated', 'success');
            await loadAll();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    // Create cleansing task
    function showCreateTask() {
        _modal('🧹 New Cleansing Rule', `
            <form onsubmit="DataFactoryView.submitCreateTask(event)">
                <div class="data-factory-form-stack">
                    <div>
                        <label>Rule Type *</label>
                        <select class="form-control" id="df_task_type" required>
                            <option value="not_null">🔒 Not Null</option>
                            <option value="unique">🔑 Unique</option>
                            <option value="range">📏 Range</option>
                            <option value="regex">🔤 Regex</option>
                            <option value="lookup">🔍 Lookup</option>
                            <option value="custom">⚙️ Custom</option>
                        </select>
                    </div>
                    <div><label>Expression *</label><input class="form-control" id="df_task_expr" required placeholder="e.g. NAME1 IS NOT NULL"></div>
                    <div><label>Description</label><input class="form-control" id="df_task_desc"></div>
                </div>
                <div class="data-factory-modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create</button>
                </div>
            </form>
        `);
    }

    async function submitCreateTask(e) {
        e.preventDefault();
        try {
            await API.post(`/data-factory/objects/${_selectedObjectId}/tasks`, {
                rule_type: document.getElementById('df_task_type').value,
                rule_expression: document.getElementById('df_task_expr').value,
                description: document.getElementById('df_task_desc').value || null,
            });
            App.closeModal();
            App.toast('Cleansing rule created', 'success');
            await loadCleansingTasks(_selectedObjectId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    // Create load cycle
    function showCreateLoad() {
        _modal('🔄 New Load Cycle', `
            <form onsubmit="DataFactoryView.submitCreateLoad(event)">
                <div class="data-factory-form-stack">
                    <div>
                        <label>Environment *</label>
                        <select class="form-control" id="df_load_env" required>
                            <option value="DEV">DEV</option>
                            <option value="QAS">QAS</option>
                            <option value="PRE">PRE</option>
                            <option value="PRD">PRD</option>
                        </select>
                    </div>
                    <div>
                        <label>Load Type *</label>
                        <select class="form-control" id="df_load_type" required>
                            <option value="initial">Initial</option>
                            <option value="delta">Delta</option>
                            <option value="full_reload">Full Reload</option>
                            <option value="mock">Mock</option>
                        </select>
                    </div>
                    <div>
                        <label>Wave (optional)</label>
                        <select class="form-control" id="df_load_wave">
                            <option value="">— No wave —</option>
                            ${_waves.map(w => `<option value="${w.id}">${esc(w.name)}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="data-factory-modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create</button>
                </div>
            </form>
        `);
    }

    async function submitCreateLoad(e) {
        e.preventDefault();
        try {
            const waveVal = document.getElementById('df_load_wave').value;
            await API.post(`/data-factory/objects/${_selectedObjectId}/loads`, {
                environment: document.getElementById('df_load_env').value,
                load_type: document.getElementById('df_load_type').value,
                wave_id: waveVal ? parseInt(waveVal) : null,
            });
            App.closeModal();
            App.toast('Load cycle created', 'success');
            await loadLoadCycles(_selectedObjectId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    // ══════════════════════════════════════════════════════════════════════
    // ACTIONS — run / start / complete / delete / reconciliation
    // ══════════════════════════════════════════════════════════════════════

    async function runTask(taskId) {
        try {
            await API.post(`/data-factory/tasks/${taskId}/run`, {});
            App.toast('Cleansing task executed', 'success');
            await loadCleansingTasks(_selectedObjectId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function deleteTask(taskId) {
        const confirmed = await App.confirmDialog({
            title: 'Delete Cleansing Rule',
            message: 'Delete this cleansing rule?',
            confirmLabel: 'Delete',
            testId: 'data-factory-delete-task-modal',
            confirmTestId: 'data-factory-delete-task-submit',
            cancelTestId: 'data-factory-delete-task-cancel',
        });
        if (!confirmed) return;
        try {
            await API.delete(`/data-factory/tasks/${taskId}`);
            App.toast('Rule deleted', 'success');
            await loadCleansingTasks(_selectedObjectId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function startLoad(lcId) {
        try {
            await API.post(`/data-factory/loads/${lcId}/start`, {});
            App.toast('Load cycle started', 'success');
            await loadLoadCycles(_selectedObjectId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function completeLoad(lcId) {
        _modal('✓ Complete Load Cycle', `
            <form onsubmit="DataFactoryView.submitCompleteLoad(event, ${lcId})">
                <div class="data-factory-form-stack">
                    <div><label>Records Loaded</label><input type="number" class="form-control" id="df_comp_loaded" value="0" min="0"></div>
                    <div><label>Records Failed</label><input type="number" class="form-control" id="df_comp_failed" value="0" min="0"></div>
                    <div><label>Error Log (if any)</label><textarea class="form-control" id="df_comp_error" rows="2"></textarea></div>
                </div>
                <div class="data-factory-modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Complete</button>
                </div>
            </form>
        `);
    }

    async function submitCompleteLoad(e, lcId) {
        e.preventDefault();
        try {
            await API.post(`/data-factory/loads/${lcId}/complete`, {
                records_loaded: parseInt(document.getElementById('df_comp_loaded').value) || 0,
                records_failed: parseInt(document.getElementById('df_comp_failed').value) || 0,
                error_log: document.getElementById('df_comp_error').value || null,
            });
            App.closeModal();
            App.toast('Load cycle completed', 'success');
            await loadLoadCycles(_selectedObjectId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function deleteObject(objId) {
        const confirmed = await App.confirmDialog({
            title: 'Delete Data Object',
            message: 'Delete this data object and all its tasks/loads?',
            confirmLabel: 'Delete',
            testId: 'data-factory-delete-object-modal',
            confirmTestId: 'data-factory-delete-object-submit',
            cancelTestId: 'data-factory-delete-object-cancel',
        });
        if (!confirmed) return;
        try {
            await API.delete(`/data-factory/objects/${objId}`);
            App.toast('Data object deleted', 'success');
            await loadAll();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function deleteWave(waveId) {
        const confirmed = await App.confirmDialog({
            title: 'Delete Migration Wave',
            message: 'Delete this migration wave?',
            confirmLabel: 'Delete',
            testId: 'data-factory-delete-wave-modal',
            confirmTestId: 'data-factory-delete-wave-submit',
            cancelTestId: 'data-factory-delete-wave-cancel',
        });
        if (!confirmed) return;
        try {
            await API.delete(`/data-factory/waves/${waveId}`);
            App.toast('Wave deleted', 'success');
            await loadAll();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function showReconciliations(lcId) {
        try {
            const recons = await API.get(`/data-factory/loads/${lcId}/recons`);
            const list = Array.isArray(recons) ? recons : (recons.items || []);

            _modal(`Reconciliations — Load #${lcId}`, list.length === 0
                ? `<p class="data-factory-empty-inline">No reconciliation records.</p>
                   <button class="btn btn-primary btn-sm" onclick="DataFactoryView.createRecon(${lcId})">+ Add Reconciliation</button>`
                : `
                <table class="data-table data-factory-table">
                    <thead>
                        <tr><th>Source</th><th>Target</th><th>Match</th><th>Variance</th><th>%</th><th>Status</th><th>Notes</th><th></th></tr>
                    </thead>
                    <tbody>
                        ${list.map(r => `
                            <tr>
                                <td class="data-factory-table-cell--right">${fmtNum(r.source_count)}</td>
                                <td class="data-factory-table-cell--right">${fmtNum(r.target_count)}</td>
                                <td class="data-factory-table-cell--right">${fmtNum(r.match_count)}</td>
                                <td class="data-factory-table-cell--right data-factory-cell-copy ${r.variance === 0 ? 'data-factory-cell-copy--success' : 'data-factory-cell-copy--danger'}">${fmtNum(r.variance)}</td>
                                <td>${fmtPct(r.variance_pct)}</td>
                                <td>${_badge(r.status)}</td>
                                <td class="data-factory-cell-copy data-factory-cell-copy--small">${esc(r.notes || '')}</td>
                                <td><button class="btn btn-sm btn-secondary" onclick="DataFactoryView.calcRecon(${r.id}, ${lcId})">Calc</button></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <button class="btn btn-primary btn-sm" onclick="DataFactoryView.createRecon(${lcId})">+ Add Reconciliation</button>
            `);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function createRecon(lcId) {
        App.closeModal();
        _modal('🔎 New Reconciliation', `
            <form onsubmit="DataFactoryView.submitCreateRecon(event, ${lcId})">
                <div class="data-factory-form-stack">
                    <div><label>Source Count</label><input type="number" class="form-control" id="df_recon_src" value="0" min="0"></div>
                    <div><label>Target Count</label><input type="number" class="form-control" id="df_recon_tgt" value="0" min="0"></div>
                    <div><label>Match Count</label><input type="number" class="form-control" id="df_recon_match" value="0" min="0"></div>
                </div>
                <div class="data-factory-modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create & Calculate</button>
                </div>
            </form>
        `);
    }

    async function submitCreateRecon(e, lcId) {
        e.preventDefault();
        try {
            const created = await API.post(`/data-factory/loads/${lcId}/recons`, {
                source_count: parseInt(document.getElementById('df_recon_src').value) || 0,
                target_count: parseInt(document.getElementById('df_recon_tgt').value) || 0,
                match_count: parseInt(document.getElementById('df_recon_match').value) || 0,
            });
            // Auto-calculate
            await API.post(`/data-factory/recons/${created.id}/calculate`, {});
            App.closeModal();
            App.toast('Reconciliation created & calculated', 'success');
            showReconciliations(lcId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function calcRecon(reconId, lcId) {
        try {
            await API.post(`/data-factory/recons/${reconId}/calculate`, {});
            App.toast('Reconciliation calculated', 'success');
            App.closeModal();
            showReconciliations(lcId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    function _renderAIDataList(title, items, renderItem) {
        const list = Array.isArray(items) ? items.filter(Boolean) : [];
        if (!list.length) return '';
        return `
            <div class="data-factory-ai-list">
                <h3 class="data-factory-ai-list__title">${esc(title)}</h3>
                <ul class="data-factory-ai-list__items">
                    ${list.map((item) => `<li>${renderItem ? renderItem(item) : esc(String(item))}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    function showAIQualityModal() {
        if (!_objects.length) {
            App.toast('Create or load a data object first', 'warning');
            return;
        }
        App.openModal(`
            <div class="modal-content data-factory-ai-modal">
                <div class="data-factory-ai-modal__header">
                    <h2 class="data-factory-ai-modal__title">AI Data Quality Analysis</h2>
                    <button class="btn btn-secondary btn-sm" onclick="App.closeModal()">Close</button>
                </div>
                <div class="data-factory-ai-modal__grid data-factory-ai-modal__grid--quality">
                    <div>
                        <label for="aiQualityObjectId" class="data-factory-ai-modal__label">Data Object</label>
                        <select id="aiQualityObjectId" class="form-control">
                            ${_objects.map((obj) => `<option value="${obj.id}">${esc(obj.name)}${obj.source_system ? ` • ${esc(obj.source_system)}` : ''}</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label for="aiQualityType" class="data-factory-ai-modal__label">Analysis Type</label>
                        <select id="aiQualityType" class="form-control">
                            <option value="completeness">Completeness</option>
                            <option value="consistency">Consistency</option>
                            <option value="migration_readiness">Migration Readiness</option>
                        </select>
                    </div>
                </div>
                <div class="data-factory-ai-modal__actions">
                    <button class="btn btn-primary" onclick="DataFactoryView.runAIQualityAnalysis()">Analyze</button>
                </div>
                <div id="aiQualityResult" class="data-factory-ai-modal__result"></div>
            </div>
        `);
    }

    async function runAIQualityAnalysis() {
        const container = document.getElementById('aiQualityResult');
        if (!container) return;
        const dataObjectId = parseInt(document.getElementById('aiQualityObjectId')?.value, 10);
        const analysisType = document.getElementById('aiQualityType')?.value || 'completeness';
        if (!dataObjectId) {
            container.innerHTML = '<div class="empty-state data-factory-empty"><p>Select a data object first.</p></div>';
            return;
        }
        container.innerHTML = '<div class="data-factory-ai-loading"><div class="spinner"></div></div>';
        try {
            const data = await API.post('/ai/doc-gen/data-quality', {
                data_object_id: dataObjectId,
                analysis_type: analysisType,
                create_suggestion: true,
            });
            container.innerHTML = `
                <div class="data-factory-ai-badges">
                    ${PGStatusRegistry.badge('ai', { label: `Quality ${data.quality_score || 0}` })}
                    ${PGStatusRegistry.badge('info', { label: `${data.completeness_pct || 0}% completeness` })}
                    ${data.suggestion_id ? PGStatusRegistry.badge('pending', { label: 'Suggestion queued' }) : ''}
                </div>
                <div class="data-factory-ai-card">
                    <div class="data-factory-ai-card__eyebrow">Migration Readiness</div>
                    <p class="data-factory-ai-card__copy">${esc(data.migration_readiness || 'No readiness summary returned.')}</p>
                </div>
                ${_renderAIDataList('Issues', data.issues)}
                ${_renderAIDataList('Recommendations', data.recommendations)}
                ${_renderAIDataList('Cleansing Actions', data.cleansing_actions)}
            `;
        } catch (err) {
            container.innerHTML = `<div class="empty-state data-factory-empty"><p>⚠️ ${esc(err.message)}</p></div>`;
        }
    }

    function showAIMigrationModal() {
        App.openModal(`
            <div class="modal-content data-factory-ai-modal">
                <div class="data-factory-ai-modal__header">
                    <h2 class="data-factory-ai-modal__title">AI Migration Analysis</h2>
                    <button class="btn btn-secondary btn-sm" onclick="App.closeModal()">Close</button>
                </div>
                <div class="data-factory-ai-modal__grid data-factory-ai-modal__grid--migration">
                    <div>
                        <label for="aiMigrationMode" class="data-factory-ai-modal__label">Mode</label>
                        <select id="aiMigrationMode" class="form-control">
                            <option value="analyze">Full Analysis</option>
                            <option value="optimize-waves">Optimize Waves</option>
                            <option value="reconciliation">Reconciliation</option>
                        </select>
                    </div>
                    <div>
                        <label for="aiMigrationTarget" class="data-factory-ai-modal__label">Data Object / Target (optional)</label>
                        <input id="aiMigrationTarget" class="form-control" placeholder="e.g. Vendor Master">
                    </div>
                    <div>
                        <label for="aiMigrationScope" class="data-factory-ai-modal__label">Scope</label>
                        <select id="aiMigrationScope" class="form-control">
                            <option value="full">Full</option>
                            <option value="delta">Delta</option>
                            <option value="initial_load">Initial Load</option>
                        </select>
                    </div>
                    <div>
                        <label for="aiMigrationParallel" class="data-factory-ai-modal__label">Max Parallel Streams</label>
                        <input id="aiMigrationParallel" class="form-control" type="number" min="1" value="3">
                    </div>
                </div>
                <div class="data-factory-ai-modal__actions">
                    <button class="btn btn-primary" onclick="DataFactoryView.runAIMigrationAnalysis()">Run Analysis</button>
                </div>
                <div id="aiMigrationResult" class="data-factory-ai-modal__result"></div>
            </div>
        `);
    }

    async function runAIMigrationAnalysis() {
        const container = document.getElementById('aiMigrationResult');
        if (!_pid || !container) return;
        const mode = document.getElementById('aiMigrationMode')?.value || 'analyze';
        const scope = document.getElementById('aiMigrationScope')?.value || 'full';
        const maxParallel = parseInt(document.getElementById('aiMigrationParallel')?.value, 10) || 3;
        const dataObject = (document.getElementById('aiMigrationTarget')?.value || '').trim();
        const path = mode === 'optimize-waves'
            ? '/ai/migration/optimize-waves'
            : mode === 'reconciliation'
                ? '/ai/migration/reconciliation'
                : '/ai/migration/analyze';
        const payload = { program_id: _pid, create_suggestion: true };
        if (mode === 'analyze') payload.scope = scope;
        if (mode === 'optimize-waves') payload.max_parallel = maxParallel;
        if (mode === 'reconciliation' && dataObject) payload.data_object = dataObject;

        container.innerHTML = '<div class="data-factory-ai-loading"><div class="spinner"></div></div>';
        try {
            const data = await API.post(path, payload);
            container.innerHTML = `
                <div class="data-factory-ai-badges">
                    ${PGStatusRegistry.badge('ai', { label: esc(mode.replace(/-/g, ' ')) })}
                    ${data.confidence != null ? PGStatusRegistry.badge('info', { label: `${Math.round((data.confidence || 0) * 100)}% confidence` }) : ''}
                    ${data.suggestion_id ? PGStatusRegistry.badge('pending', { label: 'Suggestion queued' }) : ''}
                </div>
                ${data.strategy ? `
                    <div class="data-factory-ai-card">
                        <div class="data-factory-ai-card__eyebrow">Strategy</div>
                        <p class="data-factory-ai-card__copy">${esc(data.strategy)}</p>
                    </div>
                ` : ''}
                ${data.summary ? `
                    <div class="data-factory-ai-card">
                        <div class="data-factory-ai-card__eyebrow">Summary</div>
                        <p class="data-factory-ai-card__copy">${esc(data.summary)}</p>
                    </div>
                ` : ''}
                ${_renderAIDataList('Wave Sequence', data.wave_sequence || data.optimized_sequence, (item) => esc(typeof item === 'object' ? JSON.stringify(item) : String(item)))}
                ${_renderAIDataList('Parallel Groups', data.parallel_groups, (item) => esc(Array.isArray(item) ? item.join(', ') : String(item)))}
                ${_renderAIDataList('Critical Path', data.critical_path)}
                ${_renderAIDataList('Risk Areas', data.risk_areas)}
                ${_renderAIDataList('Recommendations', data.recommendations)}
                ${_renderAIDataList('Checks', data.checks, (item) => esc(typeof item === 'object' ? `${item.name || 'Check'}${item.category ? ` (${item.category})` : ''}` : String(item)))}
            `;
        } catch (err) {
            container.innerHTML = `<div class="empty-state data-factory-empty"><p>⚠️ ${esc(err.message)}</p></div>`;
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ══════════════════════════════════════════════════════════════════════
    return {
        render,
        switchTab,
        showCreateObject,
        submitCreateObject,
        showCreateWave,
        submitCreateWave,
        showObjectDetail,
        updateObjectStatus,
        showWaveDetail,
        updateWaveStatus,
        showCreateTask,
        submitCreateTask,
        showCreateLoad,
        submitCreateLoad,
        submitCompleteLoad,
        onCleansingObjectChange,
        onLoadObjectChange,
        runTask,
        deleteTask,
        startLoad,
        completeLoad,
        deleteObject,
        deleteWave,
        showReconciliations,
        createRecon,
        submitCreateRecon,
        calcRecon,
        showAIQualityModal,
        runAIQualityAnalysis,
        showAIMigrationModal,
        runAIMigrationAnalysis,
        setObjSearch,
        onObjFilterChange,
    };
})();
