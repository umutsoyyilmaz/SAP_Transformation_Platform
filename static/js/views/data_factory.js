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

    const STATUS_COLORS = {
        draft: '#a9b4be', profiled: '#0070f2', cleansed: '#e76500',
        ready: '#30914c', migrated: '#107e3e', archived: '#556b82',
    };
    const WAVE_COLORS = {
        planned: '#0070f2', in_progress: '#e76500', completed: '#30914c', cancelled: '#bb0000',
    };
    const LOAD_COLORS = {
        pending: '#a9b4be', running: '#0070f2', completed: '#30914c', failed: '#bb0000', aborted: '#556b82',
    };
    const RECON_COLORS = {
        pending: '#a9b4be', matched: '#30914c', variance: '#e76500', failed: '#bb0000',
    };
    const RULE_ICONS = {
        not_null: '🔒', unique: '🔑', range: '📏', regex: '🔤', lookup: '🔍', custom: '⚙️',
    };

    function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
    function fmtNum(n) { return (n ?? 0).toLocaleString('tr-TR'); }
    function fmtPct(n) { return n != null ? n.toFixed(1) + '%' : '—'; }
    function fmtDate(d) { return d ? new Date(d).toLocaleDateString('tr-TR') : '—'; }
    function fmtStatus(s) { return (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
    function qualityClass(score) {
        if (score == null) return 'badge-secondary';
        if (score >= 90) return 'badge-success';
        if (score >= 75) return 'badge-warning';
        return 'badge-danger';
    }

    // ══════════════════════════════════════════════════════════════════════
    // MAIN RENDER
    // ══════════════════════════════════════════════════════════════════════
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        _pid = prog ? prog.id : null;

        if (!_pid) {
            main.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🗄️</div>
                    <div class="empty-state__title">Data Factory</div>
                    <p>Go to <a href="#" onclick="App.navigate('programs');return false">Programs</a> to select one first.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h2>🗄️ Data Factory</h2>
                <div class="page-header__actions">
                    <button class="btn btn-primary" onclick="DataFactoryView.showCreateObject()">+ New Data Object</button>
                    <button class="btn btn-secondary" onclick="DataFactoryView.showCreateWave()">+ New Wave</button>
                </div>
            </div>
            <div class="tabs" id="dfTabs" style="margin-bottom:1rem">
                <button class="tab active" data-tab="objects" onclick="DataFactoryView.switchTab('objects')">📦 Data Objects</button>
                <button class="tab" data-tab="waves" onclick="DataFactoryView.switchTab('waves')">🌊 Migration Waves</button>
                <button class="tab" data-tab="cleansing" onclick="DataFactoryView.switchTab('cleansing')">🧹 Cleansing</button>
                <button class="tab" data-tab="loads" onclick="DataFactoryView.switchTab('loads')">🔄 Load Cycles</button>
                <button class="tab" data-tab="dashboard" onclick="DataFactoryView.switchTab('dashboard')">📊 Dashboard</button>
            </div>
            <div id="dfContent"><div style="text-align:center;padding:40px"><div class="spinner"></div></div></div>
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
            c.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📦</div>
                    <div class="empty-state__title">No data objects yet</div>
                    <p>Create your first data object to start the migration lifecycle.</p>
                    <button class="btn btn-primary" onclick="DataFactoryView.showCreateObject()">+ New Data Object</button>
                </div>`;
            return;
        }

        // Summary cards
        const total = _objects.length;
        const avgQ = _objects.filter(o => o.quality_score != null);
        const avgScore = avgQ.length ? (avgQ.reduce((s, o) => s + o.quality_score, 0) / avgQ.length).toFixed(1) : '—';
        const totalRecs = _objects.reduce((s, o) => s + (o.record_count || 0), 0);
        const readyCount = _objects.filter(o => ['ready', 'migrated'].includes(o.status)).length;

        c.innerHTML = `
            <div class="kpi-row" style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap">
                <div class="kpi-card" style="flex:1;min-width:160px;background:var(--sap-card-bg, #fff);border-radius:8px;padding:16px;box-shadow:var(--sap-shadow-sm)">
                    <div style="font-size:13px;color:var(--sap-text-secondary)">Data Objects</div>
                    <div style="font-size:28px;font-weight:700;color:var(--sap-accent)">${total}</div>
                </div>
                <div class="kpi-card" style="flex:1;min-width:160px;background:var(--sap-card-bg, #fff);border-radius:8px;padding:16px;box-shadow:var(--sap-shadow-sm)">
                    <div style="font-size:13px;color:var(--sap-text-secondary)">Avg Quality</div>
                    <div style="font-size:28px;font-weight:700;color:${parseFloat(avgScore) >= 85 ? '#30914c' : '#e76500'}">${avgScore}%</div>
                </div>
                <div class="kpi-card" style="flex:1;min-width:160px;background:var(--sap-card-bg, #fff);border-radius:8px;padding:16px;box-shadow:var(--sap-shadow-sm)">
                    <div style="font-size:13px;color:var(--sap-text-secondary)">Total Records</div>
                    <div style="font-size:28px;font-weight:700;color:var(--sap-accent)">${fmtNum(totalRecs)}</div>
                </div>
                <div class="kpi-card" style="flex:1;min-width:160px;background:var(--sap-card-bg, #fff);border-radius:8px;padding:16px;box-shadow:var(--sap-shadow-sm)">
                    <div style="font-size:13px;color:var(--sap-text-secondary)">Ready / Migrated</div>
                    <div style="font-size:28px;font-weight:700;color:#30914c">${readyCount} / ${total}</div>
                </div>
            </div>

            <div id="objFilterBar" style="margin-bottom:8px"></div>
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
                    options: Object.keys(STATUS_COLORS).map(s => ({ value: s, label: fmtStatus(s) })),
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
            actionsHtml: `<span style="font-size:12px;color:#94a3b8" id="objItemCount"></span>`,
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
            tableEl.innerHTML = '<div class="empty-state" style="padding:40px"><p>No data objects match your filters.</p></div>';
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
                        <tr onclick="DataFactoryView.showObjectDetail(${o.id})" style="cursor:pointer" class="clickable-row">
                            <td><strong>${esc(o.name)}</strong>
                                ${o.description ? `<br><small style="color:var(--sap-text-secondary)">${esc(o.description)}</small>` : ''}
                            </td>
                            <td><span class="badge badge-info">${esc(o.source_system)}</span></td>
                            <td><code>${esc(o.target_table || '—')}</code></td>
                            <td style="text-align:right">${fmtNum(o.record_count)}</td>
                            <td>
                                ${o.quality_score != null
                                    ? `<span class="badge ${qualityClass(o.quality_score)}">${o.quality_score.toFixed(1)}%</span>`
                                    : '<span class="badge badge-secondary">—</span>'}
                            </td>
                            <td><span class="badge" style="background:${STATUS_COLORS[o.status] || '#a9b4be'}22;color:${STATUS_COLORS[o.status] || '#a9b4be'}">${fmtStatus(o.status)}</span></td>
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
            c.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🌊</div>
                    <div class="empty-state__title">No migration waves defined</div>
                    <button class="btn btn-primary" onclick="DataFactoryView.showCreateWave()">+ New Wave</button>
                </div>`;
            return;
        }

        c.innerHTML = `
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px">
                ${_waves.map(w => `
                    <div class="card" onclick="DataFactoryView.showWaveDetail(${w.id})" style="border-left:4px solid ${WAVE_COLORS[w.status] || '#a9b4be'};cursor:pointer">
                        <div style="padding:16px">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                                <h3 style="margin:0;font-size:15px">🌊 ${esc(w.name)}</h3>
                                <span class="badge" style="background:${WAVE_COLORS[w.status]}22;color:${WAVE_COLORS[w.status]}">${fmtStatus(w.status)}</span>
                            </div>
                            ${w.description ? `<p style="color:var(--sap-text-secondary);font-size:13px;margin:4px 0 12px">${esc(w.description)}</p>` : ''}
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px">
                                <div><strong>Planned:</strong> ${fmtDate(w.planned_start)} → ${fmtDate(w.planned_end)}</div>
                                <div><strong>Actual:</strong> ${fmtDate(w.actual_start)} → ${fmtDate(w.actual_end)}</div>
                            </div>
                            <div style="margin-top:12px;display:flex;gap:8px">
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
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                <label style="font-weight:600">Data Object:</label>
                <select id="dfCleansingObjSelect" class="form-control" style="max-width:400px"
                        onchange="DataFactoryView.onCleansingObjectChange(this.value)">
                    ${_objects.map(o => `<option value="${o.id}" ${o.id === selId ? 'selected' : ''}>${esc(o.name)} (${esc(o.source_system)})</option>`).join('')}
                </select>
                <button class="btn btn-primary btn-sm" onclick="DataFactoryView.showCreateTask()">+ New Rule</button>
            </div>
            <div id="dfCleansingTasks"><div style="text-align:center;padding:40px"><div class="spinner"></div></div></div>
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
                <div style="display:flex;gap:12px;margin-bottom:16px">
                    <span class="badge badge-success">✓ ${passed} Passed</span>
                    <span class="badge badge-danger">✗ ${failed} Failed</span>
                    <span class="badge badge-secondary">⏳ ${pending} Pending</span>
                </div>
                <table class="data-table" style="font-size:13px">
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
                                <td><code style="font-size:12px">${esc(t.rule_expression)}</code></td>
                                <td>${esc(t.description || '')}</td>
                                <td style="text-align:right;color:#30914c">${t.pass_count != null ? fmtNum(t.pass_count) : '—'}</td>
                                <td style="text-align:right;color:#bb0000">${t.fail_count != null ? fmtNum(t.fail_count) : '—'}</td>
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
            tc.innerHTML = `<div class="empty-state"><p>⚠️ ${esc(e.message)}</p></div>`;
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
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                <label style="font-weight:600">Data Object:</label>
                <select id="dfLoadObjSelect" class="form-control" style="max-width:400px"
                        onchange="DataFactoryView.onLoadObjectChange(this.value)">
                    ${_objects.map(o => `<option value="${o.id}" ${o.id === selId ? 'selected' : ''}>${esc(o.name)} (${esc(o.source_system)})</option>`).join('')}
                </select>
                <button class="btn btn-primary btn-sm" onclick="DataFactoryView.showCreateLoad()">+ New Load Cycle</button>
            </div>
            <div id="dfLoadList"><div style="text-align:center;padding:40px"><div class="spinner"></div></div></div>
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
                <table class="data-table" style="font-size:13px">
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
                                <td style="text-align:right;color:#30914c">${c.records_loaded != null ? fmtNum(c.records_loaded) : '—'}</td>
                                <td style="text-align:right;color:#bb0000">${c.records_failed != null ? fmtNum(c.records_failed) : '—'}</td>
                                <td><span class="badge" style="background:${LOAD_COLORS[c.status] || '#a9b4be'}22;color:${LOAD_COLORS[c.status] || '#a9b4be'}">${fmtStatus(c.status)}</span></td>
                                <td>${fmtDate(c.started_at)}</td>
                                <td>${fmtDate(c.completed_at)}</td>
                                <td>
                                    <button class="btn btn-sm btn-secondary" onclick="DataFactoryView.showReconciliations(${c.id})">Recon</button>
                                    ${c.status === 'pending' ? `<button class="btn btn-sm btn-primary" onclick="DataFactoryView.startLoad(${c.id})">▶ Start</button>` : ''}
                                    ${c.status === 'running' ? `<button class="btn btn-sm btn-success" onclick="DataFactoryView.completeLoad(${c.id})">✓ Complete</button>` : ''}
                                </td>
                            </tr>
                            ${c.error_log ? `<tr><td colspan="9" style="background:#fff3f3;color:#bb0000;font-size:12px;padding:4px 12px">⚠️ ${esc(c.error_log)}</td></tr>` : ''}
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (e) {
            lc.innerHTML = `<div class="empty-state"><p>⚠️ ${esc(e.message)}</p></div>`;
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
        c.innerHTML = `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`;

        try {
            const [qs, cc] = await Promise.all([
                API.get(`/data-factory/quality-score?program_id=${_pid}`),
                API.get(`/data-factory/cycle-comparison?program_id=${_pid}`),
            ]);

            const byStatus = qs.by_status || {};
            const envs = cc.environments || {};

            c.innerHTML = `
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">
                    <!-- Quality Score Card -->
                    <div class="card" style="padding:20px">
                        <h3 style="margin:0 0 4px">📊 Data Quality Overview</h3>
                        <p style="color:var(--sap-text-secondary);font-size:13px;margin:0 0 16px">${qs.total_objects} objects</p>
                        <div style="display:flex;align-items:center;gap:20px;margin-bottom:16px">
                            <div style="text-align:center">
                                <div style="font-size:48px;font-weight:700;color:${qs.avg_quality_score >= 85 ? '#30914c' : qs.avg_quality_score >= 70 ? '#e76500' : '#bb0000'}">
                                    ${qs.avg_quality_score ? qs.avg_quality_score.toFixed(1) : '0'}%
                                </div>
                                <div style="font-size:12px;color:var(--sap-text-secondary)">Avg Quality Score</div>
                            </div>
                            <div style="flex:1">
                                <canvas id="dfQualityChart" height="180"></canvas>
                            </div>
                        </div>
                    </div>

                    <!-- Status Breakdown Card -->
                    <div class="card" style="padding:20px">
                        <h3 style="margin:0 0 16px">📦 Object Status Breakdown</h3>
                        <div style="display:flex;flex-wrap:wrap;gap:12px">
                            ${Object.entries(byStatus).map(([s, cnt]) => `
                                <div style="text-align:center;min-width:80px;padding:12px;border-radius:8px;background:${STATUS_COLORS[s] || '#a9b4be'}11">
                                    <div style="font-size:24px;font-weight:700;color:${STATUS_COLORS[s] || '#a9b4be'}">${cnt}</div>
                                    <div style="font-size:12px;color:var(--sap-text-secondary)">${fmtStatus(s)}</div>
                                </div>
                            `).join('')}
                        </div>
                        ${Object.keys(byStatus).length === 0 ? '<p style="color:var(--sap-text-secondary)">No data yet.</p>' : ''}
                    </div>
                </div>

                <!-- Environment Comparison -->
                <div class="card" style="padding:20px">
                    <h3 style="margin:0 0 16px">🔄 Environment Load Comparison</h3>
                    ${Object.keys(envs).length === 0
                        ? '<p style="color:var(--sap-text-secondary)">No load cycles yet.</p>'
                        : `
                        <table class="data-table" style="font-size:13px">
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
                                        <td style="text-align:right">${d.total}</td>
                                        <td style="text-align:right;color:#30914c">${d.completed}</td>
                                        <td style="text-align:right;color:#bb0000">${d.failed}</td>
                                        <td style="text-align:right">${fmtNum(d.records_loaded)}</td>
                                        <td style="text-align:right;color:#bb0000">${fmtNum(d.records_failed)}</td>
                                        <td>
                                            <div style="display:flex;align-items:center;gap:8px">
                                                <div style="flex:1;height:8px;background:#e8e8e8;border-radius:4px;overflow:hidden">
                                                    <div style="width:${rate}%;height:100%;background:${parseInt(rate) >= 80 ? '#30914c' : '#e76500'};border-radius:4px"></div>
                                                </div>
                                                <span style="font-weight:600;font-size:12px">${rate}%</span>
                                            </div>
                                        </td>
                                    </tr>`;
                                }).join('')}
                            </tbody>
                        </table>
                        <div style="margin-top:20px"><canvas id="dfEnvChart" height="200"></canvas></div>
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
            <div class="modal-body" style="max-height:65vh;overflow-y:auto">
                ${body}
            </div>
        `);
    }

    async function showCreateObject() {
        const members = await TeamMemberPicker.fetchMembers(_pid);
        const ownerHtml = TeamMemberPicker.renderSelect('df_obj_owner', members, '', { cssClass: 'form-control', placeholder: '— Select Owner —' });
        _modal('📦 New Data Object', `
            <form onsubmit="DataFactoryView.submitCreateObject(event)">
                <div style="display:grid;gap:12px">
                    <div><label>Name *</label><input class="form-control" id="df_obj_name" required></div>
                    <div><label>Source System *</label><input class="form-control" id="df_obj_source" required placeholder="SAP ECC, Legacy HR, etc."></div>
                    <div><label>Target Table</label><input class="form-control" id="df_obj_target" placeholder="S/4HANA target table"></div>
                    <div><label>Record Count</label><input type="number" class="form-control" id="df_obj_records" value="0"></div>
                    <div><label>Owner</label>${ownerHtml}</div>
                    <div><label>Description</label><textarea class="form-control" id="df_obj_desc" rows="2"></textarea></div>
                </div>
                <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
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
                <div style="display:grid;gap:12px">
                    <div><label>Wave Number *</label><input type="number" class="form-control" id="df_wave_num" required min="1"></div>
                    <div><label>Name *</label><input class="form-control" id="df_wave_name" required></div>
                    <div><label>Description</label><textarea class="form-control" id="df_wave_desc" rows="2"></textarea></div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
                        <div><label>Planned Start</label><input type="date" class="form-control" id="df_wave_start"></div>
                        <div><label>Planned End</label><input type="date" class="form-control" id="df_wave_end"></div>
                    </div>
                </div>
                <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
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
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px;margin-bottom:16px">
                    <div><strong>Source:</strong> ${esc(obj.source_system)}</div>
                    <div><strong>Target:</strong> <code>${esc(obj.target_table || '—')}</code></div>
                    <div><strong>Records:</strong> ${fmtNum(obj.record_count)}</div>
                    <div><strong>Quality:</strong> ${obj.quality_score != null ? obj.quality_score.toFixed(1) + '%' : '—'}</div>
                    <div><strong>Status:</strong> <span class="badge" style="background:${STATUS_COLORS[obj.status]}22;color:${STATUS_COLORS[obj.status]}">${fmtStatus(obj.status)}</span></div>
                    <div><strong>Owner:</strong> ${esc(obj.owner || '—')}</div>
                </div>
                ${obj.description ? `<p style="color:var(--sap-text-secondary);font-size:13px">${esc(obj.description)}</p>` : ''}
                <div style="display:flex;gap:12px;font-size:13px;color:var(--sap-text-secondary)">
                    <span>🧹 ${obj.task_count ?? 0} cleansing tasks</span>
                    <span>🔄 ${obj.load_count ?? 0} load cycles</span>
                </div>
                <div style="margin-top:16px">
                    <label style="font-weight:600">Update Status:</label>
                    <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
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
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px;margin-bottom:16px">
                    <div><strong>Wave #:</strong> ${wave.wave_number}</div>
                    <div><strong>Status:</strong> <span class="badge" style="background:${WAVE_COLORS[wave.status]}22;color:${WAVE_COLORS[wave.status]}">${fmtStatus(wave.status)}</span></div>
                    <div><strong>Planned:</strong> ${fmtDate(wave.planned_start)} → ${fmtDate(wave.planned_end)}</div>
                    <div><strong>Actual:</strong> ${fmtDate(wave.actual_start)} → ${fmtDate(wave.actual_end)}</div>
                    <div><strong>Load Cycles:</strong> ${wave.load_cycle_count ?? 0}</div>
                    <div><strong>Records Loaded:</strong> ${fmtNum(wave.total_loaded)}</div>
                </div>
                ${wave.description ? `<p style="color:var(--sap-text-secondary);font-size:13px">${esc(wave.description)}</p>` : ''}
                <div style="margin-top:16px">
                    <label style="font-weight:600">Update Status:</label>
                    <div style="display:flex;gap:8px;margin-top:8px">
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
                <div style="display:grid;gap:12px">
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
                <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
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
                <div style="display:grid;gap:12px">
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
                <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
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
        if (!confirm('Delete this cleansing rule?')) return;
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
                <div style="display:grid;gap:12px">
                    <div><label>Records Loaded</label><input type="number" class="form-control" id="df_comp_loaded" value="0" min="0"></div>
                    <div><label>Records Failed</label><input type="number" class="form-control" id="df_comp_failed" value="0" min="0"></div>
                    <div><label>Error Log (if any)</label><textarea class="form-control" id="df_comp_error" rows="2"></textarea></div>
                </div>
                <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
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
        if (!confirm('Delete this data object and all its tasks/loads?')) return;
        try {
            await API.delete(`/data-factory/objects/${objId}`);
            App.toast('Data object deleted', 'success');
            await loadAll();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function deleteWave(waveId) {
        if (!confirm('Delete this migration wave?')) return;
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

            _modal(`🔎 Reconciliations — Load #${lcId}`, list.length === 0
                ? `<p style="color:var(--sap-text-secondary)">No reconciliation records.</p>
                   <button class="btn btn-primary btn-sm" onclick="DataFactoryView.createRecon(${lcId})">+ Add Reconciliation</button>`
                : `
                <table class="data-table" style="font-size:13px">
                    <thead>
                        <tr><th>Source</th><th>Target</th><th>Match</th><th>Variance</th><th>%</th><th>Status</th><th>Notes</th><th></th></tr>
                    </thead>
                    <tbody>
                        ${list.map(r => `
                            <tr>
                                <td style="text-align:right">${fmtNum(r.source_count)}</td>
                                <td style="text-align:right">${fmtNum(r.target_count)}</td>
                                <td style="text-align:right">${fmtNum(r.match_count)}</td>
                                <td style="text-align:right;color:${r.variance === 0 ? '#30914c' : '#bb0000'}">${fmtNum(r.variance)}</td>
                                <td>${fmtPct(r.variance_pct)}</td>
                                <td><span class="badge" style="background:${RECON_COLORS[r.status]}22;color:${RECON_COLORS[r.status]}">${fmtStatus(r.status)}</span></td>
                                <td style="font-size:12px">${esc(r.notes || '')}</td>
                                <td><button class="btn btn-sm btn-secondary" onclick="DataFactoryView.calcRecon(${r.id}, ${lcId})">Calc</button></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <button class="btn btn-primary btn-sm" style="margin-top:12px" onclick="DataFactoryView.createRecon(${lcId})">+ Add Reconciliation</button>
            `);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function createRecon(lcId) {
        App.closeModal();
        _modal('🔎 New Reconciliation', `
            <form onsubmit="DataFactoryView.submitCreateRecon(event, ${lcId})">
                <div style="display:grid;gap:12px">
                    <div><label>Source Count</label><input type="number" class="form-control" id="df_recon_src" value="0" min="0"></div>
                    <div><label>Target Count</label><input type="number" class="form-control" id="df_recon_tgt" value="0" min="0"></div>
                    <div><label>Match Count</label><input type="number" class="form-control" id="df_recon_match" value="0" min="0"></div>
                </div>
                <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
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
        setObjSearch,
        onObjFilterChange,
    };
})();
