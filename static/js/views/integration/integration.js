/**
 * SAP Transformation Platform — Integration Factory View (Sprint 9)
 *
 * 4-tab layout:
 *   1. Interface Inventory — list + CRUD
 *   2. Wave Planning — wave list + kanban-style assignment
 *   3. Connectivity Dashboard — test results per interface
 *   4. Stats — aggregated charts
 *
 * Includes readiness checklist (9.5) in interface detail modal.
 */
const IntegrationView = (() => {
    let _pid = null;
    let _interfaces = [];
    let _waves = [];
    let _stats = {};
    let _currentTab = 'inventory';
    let _pendingConfirmAction = null;

    // ── Filter state ──────────────────────────────────────────────────
    let _invSearch = '';
    let _invFilters = {};

    const DIR_ICONS  = { inbound: '⬇️', outbound: '⬆️', bidirectional: '↕️' };
    const PROTO_LABELS = {
        rfc:'RFC', idoc:'IDoc', odata:'OData', soap:'SOAP', rest:'REST',
        file:'File', pi_po:'PI/PO', cpi:'CPI', bapi:'BAPI', ale:'ALE', other:'Other',
    };
    const STATUS_COLORS = {
        identified:'#a9b4be', designed:'#0070f2', developed:'#5b738b',
        unit_tested:'#e76500', connectivity_tested:'#bb0000',
        integration_tested:'#8b47d7', go_live_ready:'#30914c', live:'#107e3e',
        decommissioned:'#556b82',
    };
    const STATUS_LABELS = {
        identified:'Identified', designed:'Designed', developed:'Developed',
        unit_tested:'Unit Tested', connectivity_tested:'Conn Tested',
        integration_tested:'Int Tested', go_live_ready:'Go-Live Ready',
        live:'Live', decommissioned:'Decommissioned',
    };
    const CONN_COLORS = { success:'#30914c', partial:'#e76500', failed:'#bb0000', pending:'#a9b4be' };

    function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
    function _activeProjectId() { return App.getActiveProject?.()?.id || null; }
    function _activeProjectName() { return App.getActiveProject?.()?.name || 'current project'; }
    async function _fetchScopedMembers() {
        return TeamMemberPicker.fetchMembers(_pid, _activeProjectId());
    }
    function _scopedProgramPath(path) {
        const projectId = _activeProjectId();
        return projectId
            ? `${path}${path.includes('?') ? '&' : '?'}project_id=${encodeURIComponent(projectId)}`
            : path;
    }

    function _deliveryNav(hub, current) {
        return typeof DeliveryHubUI !== 'undefined' && DeliveryHubUI?.nav
            ? DeliveryHubUI.nav(hub, current)
            : '';
    }

    function _openConfirmModal({ title, message, confirmLabel = 'Confirm', danger = true, onConfirm = null }) {
        _pendingConfirmAction = typeof onConfirm === 'function' ? onConfirm : null;
        App.openModal(`
            <div class="modal integration-modal integration-modal--narrow" data-testid="integration-confirm-modal">
                <div class="modal__header">
                    <h2>${esc(title || 'Confirm action')}</h2>
                    <button class="modal-close" onclick="IntegrationView.cancelConfirm()" title="Close">&times;</button>
                </div>
                <div class="modal__body">
                    <p class="integration-confirm-text">${esc(message || 'Please confirm this action.')}</p>
                </div>
                <div class="modal__footer">
                    <button class="btn btn-secondary" data-testid="integration-confirm-cancel" onclick="IntegrationView.cancelConfirm()">Cancel</button>
                    <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" data-testid="integration-confirm-submit" onclick="IntegrationView.runConfirmAction()">${esc(confirmLabel)}</button>
                </div>
            </div>`);
    }

    function cancelConfirm() {
        _pendingConfirmAction = null;
        App.closeModal();
    }

    async function runConfirmAction() {
        const action = _pendingConfirmAction;
        _pendingConfirmAction = null;
        App.closeModal();
        if (typeof action === 'function') {
            await action();
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    // MAIN RENDER
    // ══════════════════════════════════════════════════════════════════════
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        _pid = prog ? prog.id : null;

        if (!_pid) {
            main.innerHTML = PGEmptyState.html({ icon: 'integration', title: 'Integration Factory', description: 'Select a program first to continue.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header" data-testid="integration-page">
                ${PGBreadcrumb.html([{ label: 'Integration Factory' }])}
                <div class="integration-page__header-row">
                    <h2 class="pg-view-title">Integration Factory</h2>
                    <div class="integration-page__actions">
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="IntegrationView.showAIDependencyModal()">AI Dependency Map</button>
                        <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="IntegrationView.showCreateInterface()">+ New Interface</button>
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="IntegrationView.showCreateWave()">+ New Wave</button>
                    </div>
                </div>
            </div>
            ${typeof DeliveryHubUI !== 'undefined' && DeliveryHubUI?.nav
                ? DeliveryHubUI.nav('build', 'integration')
                : _deliveryNav('build', 'integration')}
            <div class="tabs integration-tabs" data-testid="integration-tabs">
                <button class="tab active" data-tab="inventory" onclick="IntegrationView.switchTab('inventory')">📋 Interface Inventory</button>
                <button class="tab" data-tab="waves" onclick="IntegrationView.switchTab('waves')">🌊 Wave Planning</button>
                <button class="tab" data-tab="connectivity" onclick="IntegrationView.switchTab('connectivity')">🔗 Connectivity</button>
                <button class="tab" data-tab="stats" onclick="IntegrationView.switchTab('stats')">📈 Stats</button>
            </div>
            <div id="integrationContent" data-testid="integration-content"><div class="integration-loading"><div class="spinner"></div></div></div>
        `;

        await loadAll();
    }

    async function loadAll() {
        try {
            const [ifaces, waves, stats] = await Promise.all([
                API.get(_scopedProgramPath(`/programs/${_pid}/interfaces`)),
                API.get(_scopedProgramPath(`/programs/${_pid}/waves`)),
                API.get(_scopedProgramPath(`/programs/${_pid}/interfaces/stats`)),
            ]);
            _interfaces = Array.isArray(ifaces) ? ifaces : (ifaces && ifaces.items) || [];
            _waves = Array.isArray(waves) ? waves : (waves && waves.items) || [];
            _stats = stats || {};
            renderTab();
        } catch (e) {
            document.getElementById('integrationContent').innerHTML =
                `<div class="empty-state"><p>⚠️ ${esc(e.message)}</p></div>`;
        }
    }

    function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('.tabs .tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        renderTab();
    }

    function renderTab() {
        const c = document.getElementById('integrationContent');
        if (_currentTab === 'inventory') renderInventory(c);
        else if (_currentTab === 'waves') renderWaves(c);
        else if (_currentTab === 'connectivity') renderConnectivity(c);
        else renderStats(c);
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 1: INTERFACE INVENTORY
    // ══════════════════════════════════════════════════════════════════════
    function renderInventory(c) {
        if (_interfaces.length === 0) {
            c.innerHTML = PGEmptyState.html({ icon: 'integration', title: 'No Interfaces Yet', description: 'Click + New Interface button to create your first interface.', action: { label: '+ New Interface', onclick: 'IntegrationView.showCreateInterface()' } });
            return;
        }

        c.innerHTML = `
            <div id="invFilterBar" class="integration-filter-bar"></div>
            <div id="invTableArea"></div>
        `;
        renderInventoryFilterBar();
        applyInventoryFilter();
    }

    function renderInventoryFilterBar() {
        const el = document.getElementById('invFilterBar');
        if (!el) return;
        el.innerHTML = ExpUI.filterBar({
            id: 'invFB',
            searchPlaceholder: 'Search interfaces…',
            searchValue: _invSearch,
            onSearch: 'IntegrationView.setInvSearch(this.value)',
            onChange: 'IntegrationView.onInvFilterChange',
            filters: [
                {
                    id: 'direction', label: 'Direction', type: 'multi', color: '#3b82f6',
                    options: ['inbound','outbound','bidirectional'].map(d => ({ value: d, label: d.charAt(0).toUpperCase() + d.slice(1) })),
                    selected: _invFilters.direction || [],
                },
                {
                    id: 'protocol', label: 'Protocol', type: 'multi', color: '#e76500',
                    options: Object.entries(PROTO_LABELS).map(([k, v]) => ({ value: k, label: v })),
                    selected: _invFilters.protocol || [],
                },
                {
                    id: 'status', label: 'Status', type: 'multi', color: '#10b981',
                    options: Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v })),
                    selected: _invFilters.status || [],
                },
                {
                    id: 'module', label: 'Module', type: 'multi', color: '#8b5cf6',
                    options: [...new Set(_interfaces.map(i => i.module).filter(Boolean))].sort().map(m => ({ value: m, label: m })),
                    selected: _invFilters.module || [],
                },
            ],
            actionsHtml: `<span class="integration-filter-count" id="invItemCount"></span>`,
        });
    }

    function setInvSearch(val) {
        _invSearch = val;
        applyInventoryFilter();
    }

    function onInvFilterChange(update) {
        if (update._clearAll) {
            _invFilters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete _invFilters[key];
                } else {
                    _invFilters[key] = val;
                }
            });
        }
        renderInventoryFilterBar();
        applyInventoryFilter();
    }

    function applyInventoryFilter() {
        let filtered = [..._interfaces];

        if (_invSearch) {
            const q = _invSearch.toLowerCase();
            filtered = filtered.filter(i =>
                (i.name || '').toLowerCase().includes(q) ||
                (i.code || '').toLowerCase().includes(q) ||
                (i.module || '').toLowerCase().includes(q) ||
                (i.source_system || '').toLowerCase().includes(q) ||
                (i.target_system || '').toLowerCase().includes(q)
            );
        }

        Object.entries(_invFilters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (values.length === 0) return;
            filtered = filtered.filter(i => values.includes(String(i[key])));
        });

        const countEl = document.getElementById('invItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${_interfaces.length}`;

        const tableEl = document.getElementById('invTableArea');
        if (!tableEl) return;
        if (filtered.length === 0) {
            tableEl.innerHTML = '<div class="empty-state integration-empty-state"><p>No interfaces match your filters.</p></div>';
            return;
        }

        const rows = filtered.map(i => `
            <tr onclick="IntegrationView.showDetail(${i.id})" class="integration-row-clickable">
                <td><strong>${esc(i.code || '—')}</strong></td>
                <td>${esc(i.name)}</td>
                <td>${DIR_ICONS[i.direction] || ''} ${esc(i.direction)}</td>
                <td>${PROTO_LABELS[i.protocol] || esc(i.protocol)}</td>
                <td>${esc(i.module || '—')}</td>
                <td>${esc(i.source_system || '—')} → ${esc(i.target_system || '—')}</td>
                <td>${_statusBadge(i.status)}</td>
                <td>${esc(i.checklist_progress)}</td>
                <td>${esc(i.priority)}</td>
            </tr>`).join('');

        tableEl.innerHTML = `
            <div class="card">
                <table class="data-table">
                    <thead><tr>
                        <th>Code</th><th>Name</th><th>Direction</th><th>Protocol</th>
                        <th>Module</th><th>Systems</th><th>Status</th><th>Checklist</th><th>Priority</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>`;
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 2: WAVE PLANNING
    // ══════════════════════════════════════════════════════════════════════
    function renderWaves(c) {
        const unassigned = _interfaces.filter(i => !i.wave_id);

        let waveCards = _waves.map(w => {
            const waveIfaces = _interfaces.filter(i => i.wave_id === w.id);
            const ifaceRows = waveIfaces.map(i => `
                <div class="wave-iface-item integration-wave-item">
                    <span>${DIR_ICONS[i.direction]||''} <strong>${esc(i.code||i.name)}</strong> — ${esc(i.name)}</span>
                    ${_statusBadge(i.status)}
                </div>`).join('') || '<p class="text-muted integration-wave-empty">No interfaces assigned</p>';

            return `
            <div class="card integration-wave-card">
                <div class="card__header integration-wave-card__header">
                    <h3>🌊 ${esc(w.name)} <span class="badge badge-${w.status}">${esc(w.status)}</span></h3>
                    <div class="integration-wave-card__actions">
                        <button class="btn btn-sm btn-secondary" onclick="IntegrationView.editWave(${w.id})">✏️</button>
                        <button class="btn btn-sm btn-danger" onclick="IntegrationView.deleteWave(${w.id})">🗑️</button>
                    </div>
                </div>
                <div class="card__body">
                    <div class="integration-wave-card__meta">
                        ${w.planned_start ? `📅 ${w.planned_start}` : ''} ${w.planned_end ? `→ ${w.planned_end}` : ''}
                        · ${waveIfaces.length} interface(s) · ${esc(w.description||'')}
                    </div>
                    ${ifaceRows}
                </div>
            </div>`;
        }).join('');

        // Unassigned pool
        const unassignedRows = unassigned.map(i => `
            <div class="integration-unassigned-item">
                <span>${DIR_ICONS[i.direction]||''} <strong>${esc(i.code||i.name)}</strong> — ${esc(i.name)}</span>
                <select onchange="IntegrationView.assignWave(${i.id}, this.value)" class="integration-wave-select">
                    <option value="">— Assign to wave —</option>
                    ${_waves.map(w => `<option value="${w.id}">${esc(w.name)}</option>`).join('')}
                </select>
            </div>`).join('') || '<p class="text-muted">All interfaces assigned to waves</p>';

        c.innerHTML = `
            ${waveCards}
            <div class="card">
                <div class="card__header"><h3>📦 Unassigned Interfaces (${unassigned.length})</h3></div>
                <div class="card__body">${unassignedRows}</div>
            </div>`;
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 3: CONNECTIVITY DASHBOARD
    // ══════════════════════════════════════════════════════════════════════
    function renderConnectivity(c) {
        if (_interfaces.length === 0) {
            c.innerHTML = '<div class="empty-state"><p>No interfaces to show connectivity status.</p></div>';
            return;
        }

        const rows = _interfaces.map(i => {
            const progress = i.checklist_progress || '0/0';
            return `
            <tr>
                <td><strong>${esc(i.code||'—')}</strong></td>
                <td>${esc(i.name)}</td>
                <td>${DIR_ICONS[i.direction]||''} ${PROTO_LABELS[i.protocol]||esc(i.protocol)}</td>
                <td>${esc(i.source_system||'—')} → ${esc(i.target_system||'—')}</td>
                <td>${_statusBadge(i.status)}</td>
                <td>${progress}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="IntegrationView.showConnTests(${i.id})">🔍 Tests</button>
                    <button class="btn btn-sm btn-primary" onclick="IntegrationView.addConnTest(${i.id})">+ Test</button>
                </td>
            </tr>`;
        }).join('');

        c.innerHTML = `
            <div class="card">
                <table class="data-table">
                    <thead><tr>
                        <th>Code</th><th>Interface</th><th>Protocol</th>
                        <th>Systems</th><th>Status</th><th>Checklist</th><th>Connectivity</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>`;
    }

    // ══════════════════════════════════════════════════════════════════════
    // TAB 4: STATS
    // ══════════════════════════════════════════════════════════════════════
    function renderStats(c) {
        const s = _stats;
        if (!s || s.total === 0) {
            c.innerHTML = '<div class="empty-state"><p>No interface data for stats.</p></div>';
            return;
        }

        const statusBars = Object.entries(s.by_status || {})
            .map(([k, v]) => _renderStatBar(STATUS_LABELS[k] || k, v, s.total, STATUS_COLORS[k] || '#0070f2'))
            .join('');

        const dirBars = Object.entries(s.by_direction || {})
            .map(([k, v]) => _renderStatBar(`${DIR_ICONS[k] || ''} ${k}`.trim(), v, s.total, '#0070f2'))
            .join('');

        const protoBars = Object.entries(s.by_protocol || {})
            .map(([k, v]) => _renderStatBar(PROTO_LABELS[k] || k, v, s.total, '#5b738b'))
            .join('');

        c.innerHTML = `
            <div class="kpi-grid integration-kpi-grid">
                <div class="kpi-card"><div class="kpi-card__value">${s.total}</div><div class="kpi-card__label">Total Interfaces</div></div>
                <div class="kpi-card"><div class="kpi-card__value">${s.by_status?.live||0}</div><div class="kpi-card__label">Live</div></div>
                <div class="kpi-card"><div class="kpi-card__value">${s.by_status?.go_live_ready||0}</div><div class="kpi-card__label">Go-Live Ready</div></div>
                <div class="kpi-card"><div class="kpi-card__value">${s.unassigned_to_wave||0}</div><div class="kpi-card__label">Unassigned</div></div>
                <div class="kpi-card"><div class="kpi-card__value">${s.total_estimated_hours||0}h</div><div class="kpi-card__label">Est. Hours</div></div>
                <div class="kpi-card"><div class="kpi-card__value">${s.total_actual_hours||0}h</div><div class="kpi-card__label">Actual Hours</div></div>
            </div>
            <div class="integration-stats-grid">
                <div class="card"><div class="card__header"><h3>By Status</h3></div><div class="card__body integration-bars">${statusBars}</div></div>
                <div class="card"><div class="card__header"><h3>By Direction</h3></div><div class="card__body integration-bars">${dirBars}</div></div>
                <div class="card"><div class="card__header"><h3>By Protocol</h3></div><div class="card__body integration-bars">${protoBars}</div></div>
            </div>`;
    }

    // ══════════════════════════════════════════════════════════════════════
    // INTERFACE DETAIL MODAL (includes Checklist — 9.5)
    // ══════════════════════════════════════════════════════════════════════
    async function showDetail(id) {
        try {
            const i = await API.get(`/interfaces/${id}`);
            const waveName = _waves.find(w => w.id === i.wave_id)?.name || '— Unassigned —';

            const checklistRows = (i.checklist || []).map(cl => `
                <tr>
                    <td class="integration-modal__check-cell">
                        <input type="checkbox" ${cl.checked ? 'checked' : ''}
                               onchange="IntegrationView.toggleChecklist(${cl.id}, this.checked)">
                    </td>
                    <td class="${cl.checked ? 'integration-modal__check-title--done' : ''}">
                        ${esc(cl.title)}
                    </td>
                    <td class="integration-modal__meta-cell">
                        ${cl.checked_by ? `✅ ${esc(cl.checked_by)}` : ''}
                        ${cl.checked_at ? `<br>${cl.checked_at.slice(0,10)}` : ''}
                    </td>
                    <td class="integration-modal__meta-cell">${esc(cl.evidence || '')}</td>
                </tr>`).join('');

            const connRows = (i.connectivity_tests || []).map(ct => `
                <tr>
                    <td>${_connBadge(ct.result)}</td>
                    <td>${esc(ct.environment)}</td>
                    <td>${ct.response_time_ms != null ? ct.response_time_ms + ' ms' : '—'}</td>
                    <td>${esc(ct.tested_by||'—')}</td>
                    <td class="integration-modal__meta-cell">${ct.tested_at ? ct.tested_at.slice(0,16).replace('T',' ') : '—'}</td>
                    <td class="integration-modal__meta-cell integration-modal__meta-cell--danger">${esc(ct.error_message||'')}</td>
                </tr>`).join('') || '<tr><td colspan="6" class="text-muted">No connectivity tests recorded</td></tr>';

            const switchRows = (i.switch_plans || []).map(sp => `
                <tr>
                    <td>${sp.sequence}</td>
                    <td><strong>${esc(sp.action)}</strong></td>
                    <td>${esc(sp.description||'')}</td>
                    <td>${esc(sp.responsible||'—')}</td>
                    <td>${sp.planned_duration_min != null ? sp.planned_duration_min + ' min' : '—'}</td>
                    <td><span class="badge badge-${sp.status}">${esc(sp.status)}</span></td>
                    <td>${sp.status !== 'completed' ? `<button class="btn btn-sm btn-primary" onclick="IntegrationView.executeSwitchPlan(${sp.id})">▶ Execute</button>` : (sp.actual_duration_min != null ? sp.actual_duration_min + ' min' : '✅')}</td>
                </tr>`).join('') || '<tr><td colspan="7" class="text-muted integration-text-muted">No switch plan entries</td></tr>';

            App.openModal(`
                <div class="modal modal--wide integration-modal integration-modal--detail" data-testid="integration-detail-modal">
                    <div class="modal__header">
                        <h2>${DIR_ICONS[i.direction]||''} ${esc(i.code||'')} ${esc(i.name)}</h2>
                        <div class="integration-modal__header-actions">
                            <button class="btn btn-secondary btn-sm" onclick="IntegrationView.editInterface(${i.id})">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="IntegrationView.deleteInterface(${i.id})">Delete</button>
                            <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
                        </div>
                    </div>
                    <div class="modal__body">
                        <!-- Header Info -->
                        <div class="integration-modal__stats-grid integration-modal__stats-grid--triple">
                            <div><strong>Direction:</strong> ${DIR_ICONS[i.direction]||''} ${esc(i.direction)}</div>
                            <div><strong>Protocol:</strong> ${PROTO_LABELS[i.protocol]||esc(i.protocol)}</div>
                            <div><strong>Middleware:</strong> ${esc(i.middleware||'—')}</div>
                            <div><strong>Source:</strong> ${esc(i.source_system||'—')}</div>
                            <div><strong>Target:</strong> ${esc(i.target_system||'—')}</div>
                            <div><strong>Module:</strong> ${esc(i.module||'—')}</div>
                            <div><strong>Status:</strong> ${_statusBadge(i.status)}</div>
                            <div><strong>Priority:</strong> ${esc(i.priority)}</div>
                            <div><strong>Wave:</strong> ${esc(waveName)}</div>
                            <div><strong>Frequency:</strong> ${esc(i.frequency||'—')}</div>
                            <div><strong>Volume:</strong> ${esc(i.volume||'—')}</div>
                            <div><strong>Message Type:</strong> ${esc(i.message_type||'—')}</div>
                            <div><strong>Complexity:</strong> ${esc(i.complexity)}</div>
                            <div><strong>Est. Hours:</strong> ${i.estimated_hours ?? '—'}</div>
                            <div><strong>Actual Hours:</strong> ${i.actual_hours ?? '—'}</div>
                        </div>
                        ${i.description ? `<div class="integration-modal__text-block"><strong>Description:</strong><br>${esc(i.description)}</div>` : ''}
                        ${i.notes ? `<div class="integration-modal__text-block"><strong>Notes:</strong><br>${esc(i.notes)}</div>` : ''}

                        <!-- Readiness Checklist (9.5) -->
                        <h3 class="integration-modal__section-title">✅ Readiness Checklist (${esc(i.checklist_progress)})</h3>
                        <table class="data-table integration-modal__table integration-modal__table--lg">
                            <thead><tr><th></th><th>Item</th><th>Checked By</th><th>Evidence</th></tr></thead>
                            <tbody>${checklistRows}</tbody>
                        </table>
                        <button class="btn btn-sm btn-secondary" onclick="IntegrationView.addChecklistItem(${i.id})">+ Custom Item</button>

                        <!-- Connectivity Tests -->
                        <h3 class="integration-modal__section-title integration-modal__section">🔗 Connectivity Tests</h3>
                        <table class="data-table integration-modal__table">
                            <thead><tr><th>Result</th><th>Environment</th><th>Response</th><th>Tester</th><th>Date</th><th>Error</th></tr></thead>
                            <tbody>${connRows}</tbody>
                        </table>
                        <button class="btn btn-sm btn-primary" onclick="IntegrationView.addConnTest(${i.id})">+ Record Test</button>

                        <!-- Switch Plan -->
                        <h3 class="integration-modal__section-title integration-modal__section">🔀 Switch Plan</h3>
                        <table class="data-table integration-modal__table">
                            <thead><tr><th>#</th><th>Action</th><th>Description</th><th>Responsible</th><th>Plan</th><th>Status</th><th></th></tr></thead>
                            <tbody>${switchRows}</tbody>
                        </table>
                        <button class="btn btn-sm btn-secondary" onclick="IntegrationView.addSwitchPlan(${i.id})">+ Add Step</button>
                    </div>
                    <div class="modal__footer">
                        <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
                    </div>
                </div>`);
        } catch (e) {
            App.toast(`Error loading interface: ${e.message}`, 'error');
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    // CREATE / EDIT INTERFACE
    // ══════════════════════════════════════════════════════════════════════
    function showCreateInterface() {
        _showInterfaceForm(null);
    }

    async function editInterface(id) {
        try {
            const i = await API.get(`/interfaces/${id}`);
            _showInterfaceForm(i);
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function _showInterfaceForm(iface) {
        const isEdit = !!iface;
        const title = isEdit ? 'Edit Interface' : 'New Interface';
        const dirs = ['inbound','outbound','bidirectional'];
        const protos = ['rfc','idoc','odata','soap','rest','file','pi_po','cpi','bapi','ale','other'];
        const statuses = ['identified','designed','developed','unit_tested','connectivity_tested','integration_tested','go_live_ready','live','decommissioned'];
        const priorities = ['low','medium','high','critical'];
        const complexities = ['low','medium','high','very_high'];
        const members = await _fetchScopedMembers();
        const assignedHtml = TeamMemberPicker.renderSelect('ifAssigned', members, iface?.assigned_to_id || iface?.assigned_to || '', { cssClass: 'form-control' });

        App.openModal(`
            <div class="modal integration-modal integration-modal--form" data-testid="integration-interface-modal">
                <div class="modal__header"><h2>${title}</h2>
                    <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button></div>
                <div class="modal__body">
                    <div class="integration-modal__banner">
                        This interface is created inside <strong>${esc(_activeProjectName())}</strong>. Waves and ownership now follow the active project scope.
                    </div>
                    <div class="integration-form-grid">
                        <div class="form-group"><label>Name *</label><input id="ifName" class="form-control" value="${esc(iface?.name||'')}"></div>
                        <div class="form-group"><label>Code</label><input id="ifCode" class="form-control" value="${esc(iface?.code||'')}" placeholder="IF-FI-001"></div>
                        <div class="form-group"><label>Direction</label>
                            <select id="ifDirection" class="form-control">${dirs.map(d=>`<option value="${d}" ${iface?.direction===d?'selected':''}>${DIR_ICONS[d]||''} ${d}</option>`).join('')}</select></div>
                        <div class="form-group"><label>Protocol</label>
                            <select id="ifProtocol" class="form-control">${protos.map(p=>`<option value="${p}" ${iface?.protocol===p?'selected':''}>${PROTO_LABELS[p]||p}</option>`).join('')}</select></div>
                        <div class="form-group"><label>Middleware</label><input id="ifMiddleware" class="form-control" value="${esc(iface?.middleware||'')}" placeholder="SAP CPI, MuleSoft..."></div>
                        <div class="form-group"><label>Module</label><input id="ifModule" class="form-control" value="${esc(iface?.module||'')}" placeholder="FI, MM, SD..."></div>
                        <div class="form-group"><label>Source System</label><input id="ifSource" class="form-control" value="${esc(iface?.source_system||'')}"></div>
                        <div class="form-group"><label>Target System</label><input id="ifTarget" class="form-control" value="${esc(iface?.target_system||'')}"></div>
                        <div class="form-group"><label>Frequency</label><input id="ifFrequency" class="form-control" value="${esc(iface?.frequency||'')}" placeholder="real-time, daily..."></div>
                        <div class="form-group"><label>Volume</label><input id="ifVolume" class="form-control" value="${esc(iface?.volume||'')}" placeholder="10K/day"></div>
                        <div class="form-group"><label>Message Type</label><input id="ifMsgType" class="form-control" value="${esc(iface?.message_type||'')}" placeholder="MATMAS, ORDERS..."></div>
                        <div class="form-group"><label>Interface Type</label>
                            <select id="ifType" class="form-control">
                                <option value="">—</option>
                                ${['master_data','transactional','reference','control'].map(t=>`<option value="${t}" ${iface?.interface_type===t?'selected':''}>${t}</option>`).join('')}
                            </select></div>
                        <div class="form-group"><label>Status</label>
                            <select id="ifStatus" class="form-control">${statuses.map(s=>`<option value="${s}" ${iface?.status===s?'selected':''}>${STATUS_LABELS[s]||s}</option>`).join('')}</select></div>
                        <div class="form-group"><label>Priority</label>
                            <select id="ifPriority" class="form-control">${priorities.map(p=>`<option value="${p}" ${iface?.priority===p?'selected':''}>${p}</option>`).join('')}</select></div>
                        <div class="form-group"><label>Complexity</label>
                            <select id="ifComplexity" class="form-control">${complexities.map(cx=>`<option value="${cx}" ${iface?.complexity===cx?'selected':''}>${cx}</option>`).join('')}</select></div>
                        <div class="form-group"><label>Wave</label>
                            <select id="ifWave" class="form-control">
                                <option value="">— No Wave —</option>
                                ${_waves.map(w=>`<option value="${w.id}" ${iface?.wave_id===w.id?'selected':''}>${esc(w.name)}</option>`).join('')}
                            </select></div>
                        <div class="form-group"><label>Assigned To</label>${assignedHtml}</div>
                        <div class="form-group"><label>Est. Hours</label><input id="ifEstHours" type="number" class="form-control" value="${iface?.estimated_hours||''}"></div>
                        <div class="form-group"><label>Go-Live Date</label><input id="ifGoLive" type="date" class="form-control" value="${iface?.go_live_date||''}"></div>
                    </div>
                    <div class="form-group integration-form-group--full"><label>Description</label><textarea id="ifDesc" class="form-control" rows="3">${esc(iface?.description||'')}</textarea></div>
                    <div class="form-group"><label>Notes</label><textarea id="ifNotes" class="form-control" rows="2">${esc(iface?.notes||'')}</textarea></div>
                </div>
                <div class="modal__footer">
                    <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button class="btn btn-primary" onclick="IntegrationView.saveInterface(${iface?.id||'null'})">${isEdit ? 'Save' : 'Create'}</button>
                </div>
            </div>`);
    }

    async function saveInterface(id) {
        const data = {
            name: document.getElementById('ifName').value.trim(),
            code: document.getElementById('ifCode').value.trim(),
            project_id: _activeProjectId(),
            direction: document.getElementById('ifDirection').value,
            protocol: document.getElementById('ifProtocol').value,
            middleware: document.getElementById('ifMiddleware').value.trim(),
            module: document.getElementById('ifModule').value.trim(),
            source_system: document.getElementById('ifSource').value.trim(),
            target_system: document.getElementById('ifTarget').value.trim(),
            frequency: document.getElementById('ifFrequency').value.trim(),
            volume: document.getElementById('ifVolume').value.trim(),
            message_type: document.getElementById('ifMsgType').value.trim(),
            interface_type: document.getElementById('ifType').value,
            status: document.getElementById('ifStatus').value,
            priority: document.getElementById('ifPriority').value,
            complexity: document.getElementById('ifComplexity').value,
            wave_id: document.getElementById('ifWave').value ? parseInt(document.getElementById('ifWave').value) : null,
            assigned_to: TeamMemberPicker.selectedMemberName('ifAssigned'),
            assigned_to_id: document.getElementById('ifAssigned').value ? parseInt(document.getElementById('ifAssigned').value) : null,
            estimated_hours: document.getElementById('ifEstHours').value ? parseFloat(document.getElementById('ifEstHours').value) : null,
            go_live_date: document.getElementById('ifGoLive').value || null,
            description: document.getElementById('ifDesc').value.trim(),
            notes: document.getElementById('ifNotes').value.trim(),
        };
        if (!data.name) { App.toast('Name is required', 'warning'); return; }

        try {
            if (id) {
                await API.put(`/interfaces/${id}`, data);
                App.toast('Interface updated', 'success');
            } else {
                await API.post(`/programs/${_pid}/interfaces`, data);
                App.toast('Interface created', 'success');
            }
            App.closeModal();
            await loadAll();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function deleteInterface(id) {
        _openConfirmModal({
            title: 'Delete interface',
            message: 'Delete this interface and all related data?',
            confirmLabel: 'Delete interface',
            onConfirm: async () => {
                try {
                    await API.delete(`/interfaces/${id}`);
                    App.toast('Interface deleted', 'success');
                    await loadAll();
                } catch (e) {
                    App.toast(`Error: ${e.message}`, 'error');
                }
            },
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    // WAVE CRUD
    // ══════════════════════════════════════════════════════════════════════
    function showCreateWave() { _showWaveForm(null); }

    async function editWave(id) {
        try {
            const w = await API.get(`/waves/${id}`);
            _showWaveForm(w);
        } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
    }

    function _showWaveForm(wave) {
        const isEdit = !!wave;
        App.openModal(`
            <div class="modal integration-modal integration-modal--narrow" data-testid="integration-wave-modal">
                <div class="modal__header"><h2>${isEdit ? 'Edit Wave' : 'New Wave'}</h2>
                    <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button></div>
                <div class="modal__body">
                    <div class="form-group"><label>Name *</label><input id="wvName" class="form-control" value="${esc(wave?.name||'')}"></div>
                    <div class="form-group"><label>Description</label><textarea id="wvDesc" class="form-control" rows="2">${esc(wave?.description||'')}</textarea></div>
                    <div class="integration-form-grid">
                        <div class="form-group"><label>Status</label>
                            <select id="wvStatus" class="form-control">
                                ${['planning','in_progress','completed','cancelled'].map(s=>`<option value="${s}" ${wave?.status===s?'selected':''}>${s}</option>`).join('')}
                            </select></div>
                        <div class="form-group"><label>Order</label><input id="wvOrder" type="number" class="form-control" value="${wave?.order||0}"></div>
                        <div class="form-group"><label>Planned Start</label><input id="wvStart" type="date" class="form-control" value="${wave?.planned_start||''}"></div>
                        <div class="form-group"><label>Planned End</label><input id="wvEnd" type="date" class="form-control" value="${wave?.planned_end||''}"></div>
                    </div>
                    <div class="form-group"><label>Notes</label><textarea id="wvNotes" class="form-control" rows="2">${esc(wave?.notes||'')}</textarea></div>
                </div>
                <div class="modal__footer">
                    <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button class="btn btn-primary" onclick="IntegrationView.saveWave(${wave?.id||'null'})">${isEdit ? 'Save' : 'Create'}</button>
                </div>
            </div>`);
    }

    async function saveWave(id) {
        const data = {
            name: document.getElementById('wvName').value.trim(),
            project_id: _activeProjectId(),
            description: document.getElementById('wvDesc').value.trim(),
            status: document.getElementById('wvStatus').value,
            order: parseInt(document.getElementById('wvOrder').value) || 0,
            planned_start: document.getElementById('wvStart').value || null,
            planned_end: document.getElementById('wvEnd').value || null,
            notes: document.getElementById('wvNotes').value.trim(),
        };
        if (!data.name) { App.toast('Name is required', 'warning'); return; }

        try {
            if (id) { await API.put(`/waves/${id}`, data); App.toast('Wave updated', 'success'); }
            else { await API.post(`/programs/${_pid}/waves`, data); App.toast('Wave created', 'success'); }
            App.closeModal();
            await loadAll();
        } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
    }

    async function deleteWave(id) {
        _openConfirmModal({
            title: 'Delete wave',
            message: 'Delete this wave? Interfaces will be unassigned.',
            confirmLabel: 'Delete wave',
            onConfirm: async () => {
                try {
                    await API.delete(`/waves/${id}`);
                    App.toast('Wave deleted', 'success');
                    await loadAll();
                } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
            },
        });
    }

    async function assignWave(ifaceId, waveId) {
        try {
            await API.patch(`/interfaces/${ifaceId}/assign-wave`, {
                project_id: _activeProjectId(),
                wave_id: waveId ? parseInt(waveId) : null,
            });
            App.toast('Wave assigned', 'success');
            await loadAll();
        } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
    }

    // ══════════════════════════════════════════════════════════════════════
    // CONNECTIVITY TESTS
    // ══════════════════════════════════════════════════════════════════════
    async function showConnTests(ifaceId) {
        try {
            const tests = await API.get(`/interfaces/${ifaceId}/connectivity-tests`);
            const iface = _interfaces.find(i => i.id === ifaceId);
            const rows = tests.map(t => `
                <tr>
                    <td>${_connBadge(t.result)}</td>
                    <td>${esc(t.environment)}</td>
                    <td>${t.response_time_ms != null ? t.response_time_ms + ' ms' : '—'}</td>
                    <td>${esc(t.tested_by||'—')}</td>
                    <td>${t.tested_at ? t.tested_at.slice(0,16).replace('T',' ') : '—'}</td>
                    <td class="integration-modal__meta-cell integration-modal__meta-cell--danger">${esc(t.error_message||'')}</td>
                </tr>`).join('') || '<tr><td colspan="6" class="text-muted integration-text-muted">No tests recorded</td></tr>';

            App.openModal(`
                <div class="modal integration-modal integration-modal--detail">
                    <div class="modal__header"><h2>🔗 Connectivity Tests — ${esc(iface?.code||iface?.name||'')}</h2>
                        <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button></div>
                    <div class="modal__body">
                        <table class="data-table">
                            <thead><tr><th>Result</th><th>Env</th><th>Response</th><th>Tester</th><th>Date</th><th>Error</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                    <div class="modal__footer">
                        <button class="btn btn-primary" onclick="IntegrationView.addConnTest(${ifaceId})">+ Record Test</button>
                        <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
                    </div>
                </div>`);
        } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
    }

    function addConnTest(ifaceId) {
        App.openModal(`
            <div class="modal integration-modal integration-modal--narrow">
                <div class="modal__header"><h2>Record Connectivity Test</h2>
                    <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button></div>
                <div class="modal__body">
                    <div class="form-group"><label>Environment</label>
                        <select id="ctEnv" class="form-control">
                            ${['dev','qas','pre_prod','prod'].map(e=>`<option value="${e}">${e}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Result</label>
                        <select id="ctResult" class="form-control">
                            ${['success','partial','failed','pending'].map(r=>`<option value="${r}">${r}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Response Time (ms)</label><input id="ctTime" type="number" class="form-control" placeholder="250"></div>
                    <div class="form-group"><label>Tested By</label><input id="ctBy" class="form-control"></div>
                    <div class="form-group"><label>Error Message</label><textarea id="ctError" class="form-control" rows="2"></textarea></div>
                    <div class="form-group"><label>Notes</label><textarea id="ctNotes" class="form-control" rows="2"></textarea></div>
                </div>
                <div class="modal__footer">
                    <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button class="btn btn-primary" onclick="IntegrationView.saveConnTest(${ifaceId})">Save</button>
                </div>
            </div>`);
    }

    async function saveConnTest(ifaceId) {
        const data = {
            environment: document.getElementById('ctEnv').value,
            result: document.getElementById('ctResult').value,
            response_time_ms: document.getElementById('ctTime').value ? parseInt(document.getElementById('ctTime').value) : null,
            tested_by: document.getElementById('ctBy').value.trim(),
            error_message: document.getElementById('ctError').value.trim(),
            notes: document.getElementById('ctNotes').value.trim(),
        };
        try {
            await API.post(`/interfaces/${ifaceId}/connectivity-tests`, data);
            App.toast('Connectivity test recorded', 'success');
            App.closeModal();
            await loadAll();
        } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
    }

    // ══════════════════════════════════════════════════════════════════════
    // SWITCH PLAN
    // ══════════════════════════════════════════════════════════════════════
    function addSwitchPlan(ifaceId) {
        App.openModal(`
            <div class="modal integration-modal integration-modal--narrow">
                <div class="modal__header"><h2>Add Switch Plan Step</h2>
                    <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button></div>
                <div class="modal__body">
                    <div class="integration-form-grid">
                        <div class="form-group"><label>Sequence #</label><input id="spSeq" type="number" class="form-control" value="1"></div>
                        <div class="form-group"><label>Action</label>
                            <select id="spAction" class="form-control">
                                ${['activate','deactivate','redirect','verify','rollback'].map(a=>`<option value="${a}">${a}</option>`).join('')}
                            </select></div>
                    </div>
                    <div class="form-group"><label>Description</label><textarea id="spDesc" class="form-control" rows="2"></textarea></div>
                    <div class="integration-form-grid">
                        <div class="form-group"><label>Responsible</label><input id="spResp" class="form-control"></div>
                        <div class="form-group"><label>Planned Duration (min)</label><input id="spDur" type="number" class="form-control"></div>
                    </div>
                </div>
                <div class="modal__footer">
                    <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button class="btn btn-primary" onclick="IntegrationView.saveSwitchPlan(${ifaceId})">Create</button>
                </div>
            </div>`);
    }

    async function saveSwitchPlan(ifaceId) {
        const data = {
            sequence: parseInt(document.getElementById('spSeq').value) || 0,
            action: document.getElementById('spAction').value,
            description: document.getElementById('spDesc').value.trim(),
            responsible: document.getElementById('spResp').value.trim(),
            planned_duration_min: document.getElementById('spDur').value ? parseInt(document.getElementById('spDur').value) : null,
        };
        try {
            await API.post(`/interfaces/${ifaceId}/switch-plans`, data);
            App.toast('Switch plan step added', 'success');
            App.closeModal();
            showDetail(ifaceId);
        } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
    }

    async function executeSwitchPlan(planId) {
        const mins = await App.promptDialog({
            title: 'Execute Switch Plan Step',
            message: 'Actual duration (minutes)',
            label: 'Duration (minutes)',
            inputType: 'number',
            confirmLabel: 'Execute',
            testId: 'integration-execute-switch-plan-modal',
        });
        if (mins === null) return;
        try {
            await API.patch(`/switch-plans/${planId}/execute`, {
                actual_duration_min: mins ? parseInt(mins) : null,
            });
            App.toast('Step executed', 'success');
            await loadAll();
        } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
    }

    // ══════════════════════════════════════════════════════════════════════
    // CHECKLIST (9.5)
    // ══════════════════════════════════════════════════════════════════════
    async function toggleChecklist(itemId, checked) {
        try {
            await API.put(`/checklist/${itemId}`, { checked, checked_by: 'User' });
        } catch (e) { App.toast(`Error: ${e.message}`, 'error'); }
    }

    async function addChecklistItem(ifaceId) {
        const title = await App.promptDialog({
            title: 'New Checklist Item',
            message: 'Checklist item title',
            label: 'Title',
            placeholder: 'Enter checklist item title',
            confirmLabel: 'Add',
            testId: 'integration-checklist-item-modal',
            required: true,
        });
        if (!title) return;
        API.post(`/interfaces/${ifaceId}/checklist`, { title })
            .then(() => { App.toast('Item added', 'success'); showDetail(ifaceId); })
            .catch(e => App.toast(`Error: ${e.message}`, 'error'));
    }

    // ── Badge helpers (token-based) ──────────────────────────────────────
    function _statusBadge(s) {
        return PGStatusRegistry.badge(s, { label: STATUS_LABELS[s] || s });
    }
    function _connBadge(result) {
        return PGStatusRegistry.badge(result);
    }

    function _renderStatBar(label, value, total, color) {
        const pct = total ? Math.round(value / total * 100) : 0;
        return `
            <div class="integration-bar-row">
                <span class="integration-bar-label">${label}</span>
                <div class="integration-bar-track">
                    <div class="integration-bar-fill" style="width:${pct}%;background:${color}"></div>
                </div>
                <span class="integration-bar-value">${value}</span>
            </div>`;
    }

    function _renderAIIntegrationList(title, items, renderItem) {
        const list = Array.isArray(items) ? items.filter(Boolean) : [];
        if (!list.length) return '';
        return `
            <div class="integration-ai-list">
                <h3 class="integration-ai-list__title">${esc(title)}</h3>
                <ul class="integration-ai-list__items">
                    ${list.map((item) => `<li>${renderItem ? renderItem(item) : esc(String(item))}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    function showAIDependencyModal() {
        App.openModal(`
            <div class="modal-content integration-ai-modal">
                <div class="integration-ai-modal__header">
                    <h2 class="integration-ai-modal__title">AI Integration Analysis</h2>
                    <button class="btn btn-secondary btn-sm" onclick="App.closeModal()">Close</button>
                </div>
                <div class="integration-ai-modal__controls">
                    <div>
                        <label for="aiIntegrationMode" class="integration-ai-modal__label">Analysis</label>
                        <select id="aiIntegrationMode" class="form-control">
                            <option value="dependencies">Dependency Map</option>
                            <option value="validate-switch">Validate Switch Plan</option>
                        </select>
                    </div>
                    <div>
                        <label for="aiSwitchPlanId" class="integration-ai-modal__label">Switch Plan ID (optional)</label>
                        <input id="aiSwitchPlanId" class="form-control" type="number" min="1" placeholder="Only used for switch validation">
                    </div>
                </div>
                <div class="integration-ai-modal__actions">
                    <button class="btn btn-primary" onclick="IntegrationView.runAIIntegrationAnalysis()">Run Analysis</button>
                </div>
                <div id="aiIntegrationResult" class="integration-ai-modal__result"></div>
            </div>
        `);
    }

    async function runAIIntegrationAnalysis() {
        const container = document.getElementById('aiIntegrationResult');
        if (!_pid || !container) return;
        const mode = document.getElementById('aiIntegrationMode')?.value || 'dependencies';
        const switchPlanId = parseInt(document.getElementById('aiSwitchPlanId')?.value, 10) || null;
        const path = mode === 'validate-switch' ? '/ai/integration/validate-switch' : '/ai/integration/dependencies';
        const payload = { program_id: _pid, create_suggestion: true };
        if (switchPlanId) payload.switch_plan_id = switchPlanId;

        container.innerHTML = '<div class="integration-ai-loading"><div class="spinner"></div></div>';

        try {
            const data = await API.post(path, payload);
            container.innerHTML = `
                <div class="integration-ai-summary">
                    ${mode === 'validate-switch'
                        ? PGStatusRegistry.badge(data.validation_status || 'info', { label: esc(String(data.validation_status || 'unknown').replace(/_/g, ' ')) })
                        : PGStatusRegistry.badge('ai', { label: `${(data.dependency_map || []).length} dependencies` })}
                    ${data.confidence != null ? PGStatusRegistry.badge('info', { label: `${Math.round((data.confidence || 0) * 100)}% confidence` }) : ''}
                </div>
                ${_renderAIIntegrationList('Dependency Map', data.dependency_map, (item) => {
                    if (typeof item !== 'object') return esc(String(item));
                    const iface = item.interface || item.name || 'Unknown';
                    const source = item.source || item.source_system || '?';
                    const target = item.target || item.target_system || '?';
                    const meta = [item.protocol, item.direction, item.criticality].filter(Boolean).join(' · ');
                    return `<strong>${esc(iface)}</strong>: ${esc(source)} → ${esc(target)}${meta ? `<div class="integration-ai-meta">${esc(meta)}</div>` : ''}`;
                })}
                ${_renderAIIntegrationList('Critical Interfaces', data.critical_interfaces, (item) => esc(typeof item === 'object' ? JSON.stringify(item) : String(item)))}
                ${_renderAIIntegrationList('Coverage Gaps', data.coverage_gaps)}
                ${_renderAIIntegrationList('Risks', data.risks)}
                ${_renderAIIntegrationList('Recommendations', data.recommendations)}
                ${_renderAIIntegrationList('Conflicts', data.conflicts)}
                ${_renderAIIntegrationList('Missing Steps', data.missing_steps)}
                ${_renderAIIntegrationList('Sequence Issues', data.sequence_issues)}
            `;
        } catch (err) {
            container.innerHTML = `<div class="empty-state integration-empty-state"><p>⚠️ ${esc(err.message)}</p></div>`;
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ══════════════════════════════════════════════════════════════════════
    return {
        render, switchTab,
        cancelConfirm, runConfirmAction,
        showDetail, showCreateInterface, editInterface, saveInterface, deleteInterface,
        showCreateWave, editWave, saveWave, deleteWave, assignWave,
        showConnTests, addConnTest, saveConnTest,
        addSwitchPlan, saveSwitchPlan, executeSwitchPlan,
        toggleChecklist, addChecklistItem,
        showAIDependencyModal, runAIIntegrationAnalysis,
        setInvSearch, onInvFilterChange,
    };
})();
