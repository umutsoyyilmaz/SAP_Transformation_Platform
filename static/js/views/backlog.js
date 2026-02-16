/**
 * SAP Transformation Management Platform
 * Backlog View — Sprint 4: WRICEF Kanban Board + Sprint Planning.
 */

const BacklogView = (() => {
    let items = [];
    let sprints = [];
    let configItems = [];
    let boardData = null;
    let currentItem = null;
    let programId = null;
    let currentTab = 'board'; // board | list | sprints | config
    let _listSearch = '';
    let _listFilters = {};
    let _configSearch = '';
    let _configFilters = {};

    // WRICEF type labels & icons
    const WRICEF = {
        workflow:    { label: 'Workflow',    icon: '🔄', color: '#0070f2' },
        report:     { label: 'Report',      icon: '📊', color: '#5b738b' },
        interface:  { label: 'Interface',   icon: '🔌', color: '#e76500' },
        conversion: { label: 'Conversion',  icon: '🔀', color: '#bb0000' },
        enhancement:{ label: 'Enhancement', icon: '⚡', color: '#30914c' },
        form:       { label: 'Form',        icon: '📄', color: '#8b47d7' },
    };

    const STATUS_LABELS = {
        new: 'New',
        design: 'Design',
        build: 'Build',
        test: 'Test',
        deploy: 'Deploy',
        closed: 'Closed',
        blocked: 'Blocked',
        cancelled: 'Cancelled',
    };

    function _priorityBadge(p) {
        const colors = { critical:'#dc2626', high:'#f97316', medium:'#f59e0b', low:'#22c55e' };
        const bg = { critical:'#fee2e2', high:'#fff7ed', medium:'#fefce8', low:'#f0fdf4' };
        const label = (p || '').charAt(0).toUpperCase() + (p || '').slice(1);
        return `<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:${bg[p] || '#f1f5f9'};color:${colors[p] || '#64748b'}">
            <span style="width:6px;height:6px;border-radius:50%;background:${colors[p] || '#94a3b8'}"></span>${label}
        </span>`;
    }

    function _statusBadge(s) {
        const map = {
            new:'#dbeafe', design:'#e0e7ff', build:'#fef3c7', test:'#fce7f3',
            deploy:'#d1fae5', closed:'#f1f5f9', blocked:'#fee2e2', cancelled:'#f1f5f9',
        };
        const textMap = {
            new:'#1e40af', design:'#3730a3', build:'#92400e', test:'#9d174d',
            deploy:'#065f46', closed:'#475569', blocked:'#991b1b', cancelled:'#475569',
        };
        const label = STATUS_LABELS[s] || s || '—';
        return `<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:${map[s] || '#f1f5f9'};color:${textMap[s] || '#475569'};white-space:nowrap">${label}</span>`;
    }

    // ── Main render ──────────────────────────────────────────────────────
    async function render() {
        currentItem = null;
        const prog = App.getActiveProgram();
        programId = prog ? prog.id : null;
        const main = document.getElementById('mainContent');

        if (!programId) {
            main.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">⚙️</div>
                    <div class="empty-state__title">Backlog</div>
                    <p>Go to <a href="#" onclick="App.navigate('programs');return false">Programs</a> to select one first.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header" style="margin-bottom:20px">
                <div>
                    <h2 style="margin:0">Backlog</h2>
                    <p style="color:#64748b;margin:4px 0 0;font-size:13px">Development objects, config items, and sprint planning</p>
                </div>
                <div class="page-header__actions">
                    ${ExpUI.actionButton({ label: '📈 Stats', variant: 'secondary', size: 'md', onclick: 'BacklogView.showStats()' })}
                    ${ExpUI.actionButton({ label: '+ New Item', variant: 'primary', size: 'md', onclick: 'BacklogView.showCreateSelector()' })}
                </div>
            </div>
            <div class="tabs" style="margin-bottom:16px">
                <button class="tab-btn ${currentTab === 'board' ? 'active' : ''}" data-tab="board" onclick="BacklogView.switchTab('board')">Kanban Board</button>
                <button class="tab-btn ${currentTab === 'list' ? 'active' : ''}" data-tab="list" onclick="BacklogView.switchTab('list')">WRICEF List</button>
                <button class="tab-btn ${currentTab === 'config' ? 'active' : ''}" data-tab="config" onclick="BacklogView.switchTab('config')">Config Items</button>
                <button class="tab-btn ${currentTab === 'sprints' ? 'active' : ''}" data-tab="sprints" onclick="BacklogView.switchTab('sprints')">Sprints</button>
            </div>
            <div id="backlogContent">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>`;

        await loadData();
    }

    function _getSelectedProgramId() {
        const prog = App.getActiveProgram();
        return prog ? prog.id : null;
    }

    async function loadData() {
        try {
            const [boardRes, sprintRes, configRes] = await Promise.all([
                API.get(`/programs/${programId}/backlog/board`),
                API.get(`/programs/${programId}/sprints`),
                API.get(`/programs/${programId}/config-items`),
            ]);
            boardData = boardRes;
            sprints = sprintRes;
            configItems = configRes;

            // Flatten board for list view
            items = [];
            Object.values(boardData.columns).forEach(col => items.push(...col));

            renderCurrentTab();
        } catch (err) {
            document.getElementById('backlogContent').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
        }
    }

    function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('.tabs .tab-btn').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        renderCurrentTab();
    }

    function renderCurrentTab() {
        if (currentTab === 'board') renderBoard();
        else if (currentTab === 'list') renderList();
        else if (currentTab === 'config') renderConfigItems();
        else renderSprints();
    }

    // ── Kanban Board ─────────────────────────────────────────────────────
    function renderBoard() {
        const c = document.getElementById('backlogContent');
        const visibleColumns = ['new', 'design', 'build', 'test', 'deploy'];
        const summary = boardData.summary;

        c.innerHTML = `
            <div class="exp-kpi-strip" style="margin-bottom:16px">
                ${ExpUI.kpiBlock({ value: summary.total_items, label: 'Items', accent: 'var(--exp-l2, #3b82f6)' })}
                ${ExpUI.kpiBlock({ value: summary.total_points, label: 'Story Points', accent: '#8b5cf6' })}
                ${ExpUI.kpiBlock({ value: summary.done_points, label: 'Done', accent: 'var(--exp-fit, #22c55e)' })}
                ${ExpUI.kpiBlock({ value: summary.completion_pct + '%', label: 'Complete', accent: summary.completion_pct >= 80 ? 'var(--exp-fit)' : summary.completion_pct >= 50 ? '#f59e0b' : 'var(--exp-gap, #ef4444)' })}
            </div>
            <div class="kanban-board">
                ${visibleColumns.map(status => `
                    <div class="kanban-column" data-status="${status}">
                        <div class="kanban-column__header">
                            <span class="kanban-column__title">${STATUS_LABELS[status]}</span>
                            <span class="kanban-column__count">${(boardData.columns[status] || []).length}</span>
                        </div>
                        <div class="kanban-column__body" data-status="${status}">
                            ${(boardData.columns[status] || []).map(item => _renderKanbanCard(item)).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>`;
    }

    function _renderKanbanCard(item) {
        const w = WRICEF[item.wricef_type] || WRICEF.enhancement;
        const linkCount = (item.requirement_id ? 1 : 0) +
                          (item.functional_spec ? 1 : 0) +
                          (item.technical_spec ? 1 : 0);
        return `
            <div class="kanban-card" data-id="${item.id}" onclick="BacklogView.openDetail(${item.id})">
                <div class="kanban-card__header">
                    <span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label[0]}</span>
                    <span class="badge badge-${item.priority}">${item.priority}</span>
                    ${linkCount > 0 ? `<span class="trace-badge" title="${linkCount} linked items">🔗${linkCount}</span>` : ''}
                </div>
                <div class="kanban-card__title">${escHtml(item.title)}</div>
                ${item.code ? `<div class="kanban-card__code">${escHtml(item.code)}</div>` : ''}
                <div class="kanban-card__footer">
                    ${item.module ? `<span class="kanban-tag">${escHtml(item.module)}</span>` : ''}
                    ${item.story_points ? `<span class="kanban-points">${item.story_points} SP</span>` : ''}
                    ${item.assigned_to ? `<span class="kanban-assignee">👤 ${escHtml(item.assigned_to)}</span>` : ''}
                </div>
            </div>`;
    }

    // ── List View ────────────────────────────────────────────────────────
    function renderList() {
        const c = document.getElementById('backlogContent');
        if (items.length === 0) {
            c.innerHTML = `
                <div class="empty-state" style="padding:40px">
                    <div class="empty-state__icon">⚙️</div>
                    <div class="empty-state__title">No backlog items yet</div>
                    <p>Create your first WRICEF item to build the development backlog.</p><br>
                    ${ExpUI.actionButton({ label: '+ New Item', variant: 'primary', size: 'md', onclick: 'BacklogView.showCreateModal()' })}
                </div>`;
            return;
        }

        c.innerHTML = `
            <div id="blFilterBar" style="margin-bottom:8px"></div>
            <div id="blListTable"></div>`;

        renderListFilterBar();
        applyListFilter();
    }

    function applyListFilter() {
        let filtered = [...items];

        if (_listSearch) {
            const q = _listSearch.toLowerCase();
            filtered = filtered.filter(i =>
                (i.title || '').toLowerCase().includes(q) ||
                (i.code || '').toLowerCase().includes(q) ||
                (i.assigned_to || '').toLowerCase().includes(q) ||
                (i.module || '').toLowerCase().includes(q)
            );
        }

        Object.entries(_listFilters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (values.length === 0) return;
            filtered = filtered.filter(i => values.includes(String(i[key])));
        });

        const countEl = document.getElementById('blItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${items.length}`;

        const tableEl = document.getElementById('blListTable');
        if (!tableEl) return;
        if (filtered.length === 0) {
            tableEl.innerHTML = '<div class="empty-state" style="padding:40px"><p>No items match your filters.</p></div>';
            return;
        }
        tableEl.innerHTML = _renderListTable(filtered);
    }

    function renderListFilterBar() {
        document.getElementById('blFilterBar').innerHTML = ExpUI.filterBar({
            id: 'blFB',
            searchPlaceholder: 'Search items…',
            searchValue: _listSearch,
            onSearch: 'BacklogView.setListSearch(this.value)',
            onChange: 'BacklogView.onListFilterChange',
            filters: [
                {
                    id: 'wricef_type', label: 'Type', type: 'multi', color: '#3b82f6',
                    options: Object.entries(WRICEF).map(([k, v]) => ({ value: k, label: v.label })),
                    selected: _listFilters.wricef_type || [],
                },
                {
                    id: 'status', label: 'Status', type: 'multi', color: '#10b981',
                    options: Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v })),
                    selected: _listFilters.status || [],
                },
                {
                    id: 'priority', label: 'Priority', type: 'multi', color: '#ef4444',
                    options: ['critical','high','medium','low'].map(p => ({ value: p, label: p.charAt(0).toUpperCase() + p.slice(1) })),
                    selected: _listFilters.priority || [],
                },
                {
                    id: 'module', label: 'Module', type: 'multi', color: '#8b5cf6',
                    options: [...new Set(items.map(i => i.module).filter(Boolean))].sort().map(m => ({ value: m, label: m })),
                    selected: _listFilters.module || [],
                },
            ],
            actionsHtml: '<span style="font-size:12px;color:#94a3b8" id="blItemCount"></span>',
        });
    }

    function setListSearch(val) {
        _listSearch = val;
        applyListFilter();
    }

    function onListFilterChange(update) {
        if (update._clearAll) {
            _listFilters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete _listFilters[key];
                } else {
                    _listFilters[key] = val;
                }
            });
        }
        renderListFilterBar();
        applyListFilter();
    }

    function _renderListTable(list) {
        let html = `<table class="data-table" style="font-size:13px">
            <thead><tr>
                <th style="width:90px">Type</th>
                <th style="width:110px">Code</th>
                <th>Title</th>
                <th style="width:60px">Module</th>
                <th style="width:80px">Status</th>
                <th style="width:85px">Priority</th>
                <th style="width:40px">SP</th>
                <th style="width:110px">Assigned</th>
                <th style="width:60px;text-align:right"></th>
            </tr></thead><tbody>`;

        list.forEach(i => {
            const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
            const linkCount = (i.requirement_id ? 1 : 0) + (i.functional_spec ? 1 : 0) + (i.technical_spec ? 1 : 0);

            html += `<tr style="cursor:pointer" onclick="BacklogView.openDetail(${i.id})">
                <td><span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label[0]}</span></td>
                <td><code style="font-size:12px;color:#475569">${escHtml(i.code || '—')}</code></td>
                <td>
                    <span style="font-weight:500">${escHtml(i.title)}</span>
                    ${linkCount > 0 ? `<span style="margin-left:4px;font-size:10px;color:#94a3b8">🔗${linkCount}</span>` : ''}
                </td>
                <td><span style="font-size:12px;color:#64748b">${escHtml(i.module || '—')}</span></td>
                <td>${_statusBadge(i.status)}</td>
                <td>${_priorityBadge(i.priority)}</td>
                <td style="text-align:center;font-weight:600;color:#64748b">${i.story_points || '—'}</td>
                <td><span style="font-size:12px;color:#64748b">${escHtml(i.assigned_to || '—')}</span></td>
                <td style="text-align:right" onclick="event.stopPropagation()">
                    <button class="btn-icon" onclick="BacklogView.openDetail(${i.id})" title="View">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
                    </button>
                    <button class="btn-icon btn-icon--danger" onclick="BacklogView.deleteItem(${i.id})" title="Delete">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
                    </button>
                </td>
            </tr>`;
        });

        html += '</tbody></table>';
        return html;
    }

    // ── Sprints Tab ──────────────────────────────────────────────────────
    function renderSprints() {
        const c = document.getElementById('backlogContent');

        c.innerHTML = `
            <div style="margin-top:12px;display:flex;justify-content:flex-end">
                ${ExpUI.actionButton({ label: '+ New Sprint', variant: 'primary', size: 'sm', onclick: 'BacklogView.showCreateSprintModal()' })}
            </div>
            ${sprints.length === 0 ? `
                <div class="empty-state" style="margin-top:20px">
                    <div class="empty-state__icon">🏃</div>
                    <div class="empty-state__title">No sprints yet</div>
                    <p>Create sprints to plan and group your backlog items into iterations.</p>
                </div>` :
                sprints.map(s => {
                    const sprintItems = items.filter(i => i.sprint_id === s.id);
                    const totalPts = sprintItems.reduce((sum, i) => sum + (i.story_points || 0), 0);
                    const donePts = sprintItems.filter(i => i.status === 'closed').reduce((sum, i) => sum + (i.story_points || 0), 0);
                    return `
                        <div class="card sprint-card" style="margin-top:16px">
                            <div class="card-header">
                                <div>
                                    <h3>${escHtml(s.name)}</h3>
                                    <span class="badge badge-${s.status}">${s.status}</span>
                                    ${s.start_date ? `<span style="color:var(--sap-text-secondary);margin-left:12px">${s.start_date} → ${s.end_date || '?'}</span>` : ''}
                                </div>
                                <div style="display:flex;gap:4px">
                                    <button class="btn-icon" onclick="BacklogView.showEditSprintModal(${s.id})" title="Edit">
                                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
                                    </button>
                                    <button class="btn-icon btn-icon--danger" onclick="BacklogView.deleteSprint(${s.id})" title="Delete">
                                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
                                    </button>
                                </div>
                            </div>
                            ${s.goal ? `<p style="margin:8px 0;color:var(--sap-text-secondary)">${escHtml(s.goal)}</p>` : ''}
                            <div class="sprint-metrics">
                                <span><strong>${sprintItems.length}</strong> items</span>
                                <span><strong>${totalPts}</strong> points</span>
                                <span><strong>${donePts}</strong> done</span>
                                ${s.capacity_points ? `<span><strong>${s.capacity_points}</strong> capacity</span>` : ''}
                                ${s.velocity != null ? `<span><strong>${s.velocity}</strong> velocity</span>` : ''}
                            </div>
                            ${sprintItems.length > 0 ? `
                                <table class="data-table" style="margin-top:12px">
                                    <thead><tr><th>Type</th><th>Code</th><th>Title</th><th>Status</th><th>SP</th></tr></thead>
                                    <tbody>
                                        ${sprintItems.map(i => {
                                            const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
                                            return `<tr onclick="BacklogView.openDetail(${i.id})" style="cursor:pointer">
                                                <td><span class="wricef-badge" style="background:${w.color}">${w.icon}</span></td>
                                                <td>${escHtml(i.code || '—')}</td>
                                                <td>${escHtml(i.title)}</td>
                                                <td><span class="badge badge-${i.status}">${STATUS_LABELS[i.status] || i.status}</span></td>
                                                <td>${i.story_points || '—'}</td>
                                            </tr>`;
                                        }).join('')}
                                    </tbody>
                                </table>` : '<p style="padding:12px;color:var(--sap-text-secondary)">No items assigned to this sprint.</p>'}
                        </div>`;
                }).join('')}
            <!-- Unassigned backlog -->
            <div class="card" style="margin-top:16px">
                <div class="card-header"><h3>Unassigned Backlog</h3></div>
                ${(() => {
                    const unassigned = items.filter(i => !i.sprint_id);
                    if (unassigned.length === 0) return '<p style="padding:12px;color:var(--sap-text-secondary)">All items are assigned to sprints.</p>';
                    return `<table class="data-table"><thead><tr><th>Type</th><th>Code</th><th>Title</th><th>Status</th><th>SP</th></tr></thead><tbody>
                        ${unassigned.map(i => {
                            const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
                            return `<tr onclick="BacklogView.openDetail(${i.id})" style="cursor:pointer">
                                <td><span class="wricef-badge" style="background:${w.color}">${w.icon}</span></td>
                                <td>${escHtml(i.code || '—')}</td><td>${escHtml(i.title)}</td>
                                <td><span class="badge badge-${i.status}">${STATUS_LABELS[i.status] || i.status}</span></td>
                                <td>${i.story_points || '—'}</td>
                            </tr>`;
                        }).join('')}
                    </tbody></table>`;
                })()}
            </div>`;
    }

    // ── Config Items Tab ────────────────────────────────────────────────
    function renderConfigItems() {
        const c = document.getElementById('backlogContent');
        c.innerHTML = `
            ${configItems.length === 0 ? `
                <div class="empty-state" style="margin-top:20px">
                    <div class="empty-state__icon">⚙️</div>
                    <div class="empty-state__title">No config items yet</div>
                    <p>Create configuration items to track SAP customizing changes.</p>
                </div>` : `
            <div id="ciFilterBar" style="margin-bottom:8px"></div>
            <div id="ciListTable"></div>`}`;

        if (configItems.length > 0) {
            renderConfigFilterBar();
            applyConfigFilter();
        }

        c.insertAdjacentHTML('beforeend', `
            <div style="margin-top:12px;display:flex;justify-content:flex-end">
                ${ExpUI.actionButton({ label: '+ New Config Item', variant: 'primary', size: 'sm', onclick: 'BacklogView.showCreateConfigModal()' })}
            </div>
        `);
    }

    function renderConfigFilterBar() {
        document.getElementById('ciFilterBar').innerHTML = ExpUI.filterBar({
            id: 'ciFB',
            searchPlaceholder: 'Search config items…',
            searchValue: _configSearch,
            onSearch: 'BacklogView.setConfigSearch(this.value)',
            onChange: 'BacklogView.onConfigFilterChange',
            filters: [
                {
                    id: 'status', label: 'Status', type: 'multi', color: '#10b981',
                    options: Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v })),
                    selected: _configFilters.status || [],
                },
                {
                    id: 'priority', label: 'Priority', type: 'multi', color: '#ef4444',
                    options: ['critical','high','medium','low'].map(p => ({ value: p, label: p.charAt(0).toUpperCase() + p.slice(1) })),
                    selected: _configFilters.priority || [],
                },
                {
                    id: 'module', label: 'Module', type: 'multi', color: '#8b5cf6',
                    options: [...new Set(configItems.map(i => i.module).filter(Boolean))].sort().map(m => ({ value: m, label: m })),
                    selected: _configFilters.module || [],
                },
            ],
            actionsHtml: '<span style="font-size:12px;color:#94a3b8" id="ciItemCount"></span>',
        });
    }

    function setConfigSearch(val) {
        _configSearch = val;
        applyConfigFilter();
    }

    function onConfigFilterChange(update) {
        if (update._clearAll) {
            _configFilters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete _configFilters[key];
                } else {
                    _configFilters[key] = val;
                }
            });
        }
        renderConfigFilterBar();
        applyConfigFilter();
    }

    function applyConfigFilter() {
        let filtered = [...configItems];

        if (_configSearch) {
            const q = _configSearch.toLowerCase();
            filtered = filtered.filter(i =>
                (i.title || '').toLowerCase().includes(q) ||
                (i.code || '').toLowerCase().includes(q) ||
                (i.assigned_to || '').toLowerCase().includes(q) ||
                (i.module || '').toLowerCase().includes(q) ||
                (i.config_key || '').toLowerCase().includes(q)
            );
        }

        Object.entries(_configFilters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (values.length === 0) return;
            filtered = filtered.filter(i => values.includes(String(i[key])));
        });

        const countEl = document.getElementById('ciItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${configItems.length}`;

        const tableEl = document.getElementById('ciListTable');
        if (!tableEl) return;
        if (filtered.length === 0) {
            tableEl.innerHTML = '<div class="empty-state" style="padding:40px"><p>No items match your filters.</p></div>';
            return;
        }

        tableEl.innerHTML = _renderConfigListTable(filtered);
    }

    function _renderConfigListTable(list) {
        let html = `<table class="data-table" style="font-size:13px">
            <thead><tr>
                <th style="width:110px">Code</th>
                <th>Title</th>
                <th style="width:60px">Module</th>
                <th>Config Key</th>
                <th style="width:80px">Status</th>
                <th style="width:85px">Priority</th>
                <th style="width:110px">Assigned</th>
                <th style="width:60px;text-align:right"></th>
            </tr></thead><tbody>`;

        list.forEach(ci => {
            html += `<tr style="cursor:pointer" onclick="BacklogView.openConfigDetail(${ci.id})">
                <td><code style="font-size:12px;color:#475569">${escHtml(ci.code || '—')}</code></td>
                <td><span style="font-weight:500">${escHtml(ci.title)}</span></td>
                <td><span style="font-size:12px;color:#64748b">${escHtml(ci.module || '—')}</span></td>
                <td><span style="font-size:12px;color:#64748b">${escHtml(ci.config_key || '—')}</span></td>
                <td>${_statusBadge(ci.status)}</td>
                <td>${_priorityBadge(ci.priority)}</td>
                <td><span style="font-size:12px;color:#64748b">${escHtml(ci.assigned_to || '—')}</span></td>
                <td style="text-align:right" onclick="event.stopPropagation()">
                    <button class="btn-icon" onclick="BacklogView.showEditConfigModal(${ci.id})" title="Edit">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
                    </button>
                    <button class="btn-icon btn-icon--danger" onclick="BacklogView.deleteConfigItem(${ci.id})" title="Delete">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
                    </button>
                </td>
            </tr>`;
        });

        html += '</tbody></table>';
        return html;
    }

    function showCreateConfigModal() { _showConfigForm(null); }

    async function showEditConfigModal(id) {
        try {
            const ci = await API.get(`/config-items/${id}`);
            _showConfigForm(ci);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function _showConfigForm(item) {
        const isEdit = !!item;
        const members = await TeamMemberPicker.fetchMembers(programId);
        const assignedHtml = TeamMemberPicker.renderSelect('ciAssigned', members, item?.assigned_to_id || item?.assigned_to || '', { cssClass: 'form-input' });
        App.openModal(`
            <h2>${isEdit ? 'Edit Config Item' : 'New Config Item'}</h2>
            <div class="form-row">
                <div class="form-group"><label>Title *</label><input id="ciTitle" class="form-input" value="${escHtml(item?.title || '')}"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Code</label><input id="ciCode" class="form-input" placeholder="e.g. CFG-FI-001" value="${escHtml(item?.code || '')}"></div>
                <div class="form-group"><label>Module</label>
                    <select id="ciModule" class="form-input">
                        <option value="">—</option>
                        ${['FI','CO','MM','SD','PP','PM','QM','HCM','PS','WM','EWM','Basis','Other'].map(m =>
                            `<option value="${m}" ${item?.module === m ? 'selected' : ''}>${m}</option>`
                        ).join('')}
                    </select>
                </div>
            </div>
            <div class="form-group"><label>Config Key / IMG Path</label><input id="ciKey" class="form-input" placeholder="e.g. SPRO > FI > Tax > Define Tax Codes" value="${escHtml(item?.config_key || '')}"></div>
            <div class="form-group"><label>Description</label><textarea id="ciDesc" class="form-input" rows="2">${escHtml(item?.description || '')}</textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Priority</label>
                    <select id="ciPriority" class="form-input">
                        ${['low','medium','high','critical'].map(p =>
                            `<option value="${p}" ${(item?.priority || 'medium') === p ? 'selected' : ''}>${p}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="form-group"><label>Assigned To</label>${assignedHtml}</div>
            </div>
            <div style="text-align:right;margin-top:16px">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="BacklogView.saveConfigItem(${isEdit ? item.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `);
    }

    async function saveConfigItem(itemId) {
        const payload = {
            title: document.getElementById('ciTitle').value.trim(),
            code: document.getElementById('ciCode').value.trim(),
            module: document.getElementById('ciModule').value,
            config_key: document.getElementById('ciKey').value.trim(),
            description: document.getElementById('ciDesc').value.trim(),
            priority: document.getElementById('ciPriority').value,
            assigned_to: document.getElementById('ciAssigned').value.trim() || null,
            assigned_to_id: document.getElementById('ciAssigned').value.trim() || null,
        };
        if (!payload.title) { App.toast('Title is required', 'error'); return; }
        try {
            if (itemId) {
                await API.put(`/config-items/${itemId}`, payload);
                App.toast('Config item updated', 'success');
            } else {
                await API.post(`/programs/${programId}/config-items`, payload);
                App.toast('Config item created', 'success');
            }
            App.closeModal();
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteConfigItem(id) {
        if (!confirm('Delete this config item?')) return;
        try {
            await API.delete(`/config-items/${id}`);
            App.toast('Config item deleted', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Config Item Detail View ──────────────────────────────────────────
    async function openConfigDetail(id) {
        let ci;
        try {
            ci = await API.get(`/config-items/${id}`);
        } catch (err) { App.toast(err.message, 'error'); return; }

        const fs = ci.functional_spec;
        const ts = fs ? fs.technical_spec : null;
        const main = document.getElementById('mainContent');

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="BacklogView.render()">← Back</button>
                    <h1 style="display:inline;margin-left:12px">
                        ⚙️ ${escHtml(ci.code || '')} ${escHtml(ci.title)}
                    </h1>
                    <span class="badge badge-${ci.status}" style="margin-left:8px">${STATUS_LABELS[ci.status] || ci.status}</span>
                </div>
                <div>
                    <button class="btn btn-primary" onclick="BacklogView.showEditConfigModal(${ci.id})">Edit</button>
                </div>
            </div>

            <div class="detail-grid">
                <div class="detail-section">
                    <h3>Classification</h3>
                    <dl class="detail-list">
                        <dt>Module</dt><dd>${escHtml(ci.module || '—')}</dd>
                        <dt>Config Key</dt><dd>${escHtml(ci.config_key || '—')}</dd>
                        <dt>Priority</dt><dd><span class="badge badge-${ci.priority}">${ci.priority}</span></dd>
                        <dt>Assigned To</dt><dd>${escHtml(ci.assigned_to || '—')}</dd>
                        <dt>Transport Request</dt><dd>${escHtml(ci.transport_request || '—')}</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Description</h3>
                    <p>${escHtml(ci.description || 'No description.')}</p>
                    ${ci.notes ? `<h4 style="margin-top:12px">Notes</h4><p>${escHtml(ci.notes)}</p>` : ''}
                </div>
            </div>

            <div class="card" style="margin-top:16px">
                <h3>📘 Functional Specification</h3>
                ${fs ? `
                    <dl class="detail-list">
                        <dt>Title</dt><dd>${escHtml(fs.title)}</dd>
                        <dt>Status</dt><dd><span class="badge badge-${fs.status}">${fs.status}</span></dd>
                        <dt>Version</dt><dd>${fs.version || '—'}</dd>
                    </dl>
                ` : '<p style="color:var(--sap-text-secondary)">No functional specification linked.</p>'}
            </div>

            <div class="card" style="margin-top:16px">
                <h3>📙 Technical Specification</h3>
                ${ts ? `
                    <dl class="detail-list">
                        <dt>Title</dt><dd>${escHtml(ts.title)}</dd>
                        <dt>Status</dt><dd><span class="badge badge-${ts.status}">${ts.status}</span></dd>
                    </dl>
                ` : '<p style="color:var(--sap-text-secondary)">No technical specification linked.</p>'}
            </div>
        `;
    }

    // ── Detail View ──────────────────────────────────────────────────────
    async function openDetail(id) {
        try {
            currentItem = await API.get(`/backlog/${id}?include_specs=true`);
        } catch (err) { App.toast(err.message, 'error'); return; }
        renderDetail();
    }

    function renderDetail() {
        const i = currentItem;
        const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
        const sprint = sprints.find(s => s.id === i.sprint_id);
        const main = document.getElementById('mainContent');

        const fs = i.functional_spec;
        const ts = i.technical_spec || (fs ? fs.technical_spec : null);

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="BacklogView.render()">← Back</button>
                    <h1 style="display:inline;margin-left:12px">
                        <span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label}</span>
                        ${escHtml(i.code || '')} ${escHtml(i.title)}
                    </h1>
                    <span class="badge badge-${i.status}" style="margin-left:8px">${STATUS_LABELS[i.status] || i.status}</span>
                </div>
                <div>
                    <button class="btn btn-secondary" onclick="BacklogView.showMoveModal()">🔀 Move</button>
                    <button class="btn btn-primary" onclick="BacklogView.showEditModal()">Edit</button>
                </div>
            </div>

            <!-- Tabs -->
            <div class="detail-tabs">
                <button class="detail-tab active" data-dtab="overview" onclick="BacklogView.switchDetailTab('overview')">📋 Overview</button>
                <button class="detail-tab" data-dtab="specs" onclick="BacklogView.switchDetailTab('specs')">📑 Specs (FS/TS)</button>
                <button class="detail-tab" data-dtab="tests" onclick="BacklogView.switchDetailTab('tests')">🧪 Tests</button>
                <button class="detail-tab" data-dtab="trace" onclick="BacklogView.switchDetailTab('trace')">🔗 Traceability</button>
            </div>

            <div id="detailTabContent"></div>
        `;

        // Render default tab
        _renderDetailOverview(i, w, sprint);
    }

    function switchDetailTab(tab) {
        document.querySelectorAll('.detail-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.dtab === tab);
        });
        const i = currentItem;
        const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
        const sprint = sprints.find(s => s.id === i.sprint_id);

        if (tab === 'overview') _renderDetailOverview(i, w, sprint);
        else if (tab === 'specs') _renderDetailSpecs(i);
        else if (tab === 'tests') _renderDetailTests(i);
        else if (tab === 'trace') _renderDetailTrace(i);
    }

    function _renderDetailOverview(i, w, sprint) {
        document.getElementById('detailTabContent').innerHTML = `
            <div class="detail-grid">
                <div class="detail-section">
                    <h3>Classification</h3>
                    <dl class="detail-list">
                        <dt>WRICEF Type</dt><dd><span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label}</span></dd>
                        <dt>Sub Type</dt><dd>${escHtml(i.sub_type || '—')}</dd>
                        <dt>Module</dt><dd>${escHtml(i.module || '—')}</dd>
                        <dt>Priority</dt><dd><span class="badge badge-${i.priority}">${i.priority}</span></dd>
                        <dt>Complexity</dt><dd>${i.complexity}</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Estimation</h3>
                    <dl class="detail-list">
                        <dt>Story Points</dt><dd>${i.story_points || '—'}</dd>
                        <dt>Estimated Hours</dt><dd>${i.estimated_hours || '—'}</dd>
                        <dt>Actual Hours</dt><dd>${i.actual_hours || '—'}</dd>
                        <dt>Sprint</dt><dd>${sprint ? escHtml(sprint.name) : 'Unassigned'}</dd>
                        <dt>Assigned To</dt><dd>${escHtml(i.assigned_to || '—')}</dd>
                    </dl>
                </div>
            </div>

            <div class="detail-grid" style="margin-top:16px">
                <div class="detail-section">
                    <h3>SAP Details</h3>
                    <dl class="detail-list">
                        <dt>Transaction Code</dt><dd>${escHtml(i.transaction_code || '—')}</dd>
                        <dt>Package</dt><dd>${escHtml(i.package || '—')}</dd>
                        <dt>Transport Request</dt><dd>${escHtml(i.transport_request || '—')}</dd>
                    </dl>
                </div>
            </div>

            <div class="card" style="margin-top:20px">
                <h3>Description</h3>
                <p>${escHtml(i.description || 'No description.')}</p>
            </div>

            ${i.acceptance_criteria ? `
            <div class="card" style="margin-top:16px">
                <h3>Acceptance Criteria</h3>
                <p>${escHtml(i.acceptance_criteria)}</p>
            </div>` : ''}

            ${i.technical_notes ? `
            <div class="card" style="margin-top:16px">
                <h3>Technical Notes</h3>
                <p>${escHtml(i.technical_notes)}</p>
            </div>` : ''}

            ${i.notes ? `
            <div class="card" style="margin-top:16px">
                <h3>Notes</h3>
                <p>${escHtml(i.notes)}</p>
            </div>` : ''}
        `;
    }

    function _renderDetailSpecs(i) {
        const fs = i.functional_spec;
        const ts = fs ? fs.technical_spec : null;
        const hasAnySpec = fs || ts;
        const needsGeneration = !fs || !ts;

        const fsActions = fs ? `
            <div style="display:flex;gap:8px;margin-top:12px">
                ${fs.status === 'draft' ? `<button class="btn btn-sm btn-primary" onclick="BacklogView.updateSpecStatus('fs', ${fs.id}, 'in_review')">📤 Submit for Review</button>` : ''}
                ${fs.status === 'in_review' ? `<button class="btn btn-sm btn-success" onclick="BacklogView.updateSpecStatus('fs', ${fs.id}, 'approved')">✅ Approve</button>
                    <button class="btn btn-sm btn-warning" onclick="BacklogView.updateSpecStatus('fs', ${fs.id}, 'rework')">🔄 Rework</button>` : ''}
                ${fs.status === 'rework' ? `<button class="btn btn-sm btn-primary" onclick="BacklogView.updateSpecStatus('fs', ${fs.id}, 'in_review')">📤 Resubmit</button>` : ''}
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.downloadSpec('fs', ${fs.id}, '${escHtml(fs.title)}')">📥 Download</button>
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.editSpec('fs', ${fs.id})">✏️ Edit</button>
            </div>
        ` : '';

        const tsActions = ts ? `
            <div style="display:flex;gap:8px;margin-top:12px">
                ${ts.status === 'draft' ? `<button class="btn btn-sm btn-primary" onclick="BacklogView.updateSpecStatus('ts', ${ts.id}, 'in_review')">📤 Submit for Review</button>` : ''}
                ${ts.status === 'in_review' ? `<button class="btn btn-sm btn-success" onclick="BacklogView.updateSpecStatus('ts', ${ts.id}, 'approved')">✅ Approve</button>
                    <button class="btn btn-sm btn-warning" onclick="BacklogView.updateSpecStatus('ts', ${ts.id}, 'rework')">🔄 Rework</button>` : ''}
                ${ts.status === 'rework' ? `<button class="btn btn-sm btn-primary" onclick="BacklogView.updateSpecStatus('ts', ${ts.id}, 'in_review')">📤 Resubmit</button>` : ''}
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.downloadSpec('ts', ${ts.id}, '${escHtml(ts.title)}')">📥 Download</button>
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.editSpec('ts', ${ts.id})">✏️ Edit</button>
            </div>
        ` : '';

        document.getElementById('detailTabContent').innerHTML = `
            ${needsGeneration ? `
            <div style="margin-top:12px;margin-bottom:16px;text-align:right">
                <button class="btn btn-primary" onclick="BacklogView._generateSpecs(${i.id})" id="btnGenerateSpecs">
                    ✨ Generate Draft from Template
                </button>
            </div>` : ''}

            <div class="card" style="margin-top:12px">
                <h3>📘 Functional Specification</h3>
                ${fs ? `
                    <dl class="detail-list">
                        <dt>Title</dt><dd>${escHtml(fs.title)}</dd>
                        <dt>Status</dt><dd><span class="badge badge-${fs.status}">${fs.status}</span></dd>
                        <dt>Version</dt><dd>${fs.version || '—'}</dd>
                        <dt>Author</dt><dd>${escHtml(fs.author || '—')}</dd>
                        <dt>Reviewer</dt><dd>${escHtml(fs.reviewer || '—')}</dd>
                        <dt>Approved By</dt><dd>${escHtml(fs.approved_by || '—')}</dd>
                    </dl>
                    ${fs.template_version ? `
                        <div style="margin-top:8px">
                            <span class="badge" style="background:#e8f4fd;color:#1a73e8;font-size:11px">
                                📋 Generated from template v${escHtml(fs.template_version)}
                            </span>
                        </div>
                    ` : ''}
                    ${fsActions}
                    ${fs.content ? `<details style="margin-top:12px"><summary style="cursor:pointer;font-weight:600">📄 FS Content (click to expand)</summary><div style="margin-top:8px;white-space:pre-wrap;background:var(--sap-bg-secondary);padding:12px;border-radius:8px;font-family:monospace;font-size:13px;max-height:500px;overflow-y:auto">${escHtml(fs.content)}</div></details>` : ''}
                ` : '<p style="color:var(--sap-text-secondary)">No functional specification linked yet.</p>'}
            </div>

            <div class="card" style="margin-top:16px">
                <h3>📙 Technical Specification</h3>
                ${ts ? `
                    <dl class="detail-list">
                        <dt>Title</dt><dd>${escHtml(ts.title)}</dd>
                        <dt>Status</dt><dd><span class="badge badge-${ts.status}">${ts.status}</span></dd>
                        <dt>Version</dt><dd>${ts.version || '—'}</dd>
                        <dt>Author</dt><dd>${escHtml(ts.author || '—')}</dd>
                        <dt>Approved By</dt><dd>${escHtml(ts.approved_by || '—')}</dd>
                    </dl>
                    ${ts.template_version ? `
                        <div style="margin-top:8px">
                            <span class="badge" style="background:#e8f4fd;color:#1a73e8;font-size:11px">
                                📋 Generated from template v${escHtml(ts.template_version)}
                            </span>
                        </div>
                    ` : ''}
                    ${tsActions}
                    ${ts.content ? `<details style="margin-top:12px"><summary style="cursor:pointer;font-weight:600">📄 TS Content (click to expand)</summary><div style="margin-top:8px;white-space:pre-wrap;background:var(--sap-bg-secondary);padding:12px;border-radius:8px;font-family:monospace;font-size:13px;max-height:500px;overflow-y:auto">${escHtml(ts.content)}</div></details>` : ''}
                ` : `<p style="color:var(--sap-text-secondary)">${fs ? 'Technical spec will be auto-created when FS is approved.' : 'No technical specification linked yet.'}</p>`}
            </div>
        `;
    }

    async function _generateSpecs(itemId) {
        const btn = document.getElementById('btnGenerateSpecs');
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⏳ Generating...';
        }
        try {
            const result = await API.post(`/backlog/${itemId}/generate-specs`);
            App.toast('FS/TS drafts generated successfully!', 'success');
            // Reload detail to show generated specs
            await openDetail(currentItem.id);
            switchDetailTab('specs');
        } catch (err) {
            App.toast(err.message || 'Failed to generate specs', 'error');
            if (btn) {
                btn.disabled = false;
                btn.textContent = '✨ Generate Draft from Template';
            }
        }
    }

    async function _renderDetailTests(i) {
        const container = document.getElementById('detailTabContent');
        container.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';
        try {
            const chain = await API.get(`/traceability/backlog_item/${i.id}`);
            const testCases = (chain.downstream || []).filter(d => d.type === 'test_case');
            const defects = (chain.downstream || []).filter(d => d.type === 'defect');

            container.innerHTML = `
                <div class="card" style="margin-top:12px">
                    <h3>🧪 Linked Test Cases (${testCases.length})</h3>
                    ${testCases.length > 0 ? `
                        <table class="data-table">
                            <thead><tr><th>Code</th><th>Title</th><th>Layer</th></tr></thead>
                            <tbody>${testCases.map(tc => `
                                <tr>
                                    <td>${escHtml(tc.code || '—')}</td>
                                    <td>${escHtml(tc.title)}</td>
                                    <td>${escHtml(tc.test_layer || '—')}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>` : '<p style="color:var(--sap-text-secondary)">No test cases linked.</p>'}
                </div>
                <div class="card" style="margin-top:16px">
                    <h3>🐛 Linked Defects (${defects.length})</h3>
                    ${defects.length > 0 ? `
                        <table class="data-table">
                            <thead><tr><th>Code</th><th>Title</th><th>Severity</th><th>Status</th></tr></thead>
                            <tbody>${defects.map(d => `
                                <tr>
                                    <td>${escHtml(d.code || '—')}</td>
                                    <td>${escHtml(d.title)}</td>
                                    <td>${escHtml(d.severity || '—')}</td>
                                    <td><span class="badge badge-${d.status}">${d.status}</span></td>
                                </tr>`).join('')}
                            </tbody>
                        </table>` : '<p style="color:var(--sap-text-secondary)">No defects linked.</p>'}
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div class="card" style="margin-top:12px"><p>Could not load test data.</p></div>`;
        }
    }

    async function _renderDetailTrace(i) {
        const container = document.getElementById('detailTabContent');
        // Use unified TraceChain component if available
        if (typeof TraceChain !== 'undefined') {
            await TraceChain.renderInTab('backlog_item', i.id, container);
            return;
        }
        // Fallback: basic table rendering
        container.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';
        try {
            const chain = await API.get(`/traceability/backlog_item/${i.id}`);
            const upstream = chain.upstream || [];
            const downstream = chain.downstream || [];

            container.innerHTML = `
                <div class="card" style="margin-top:12px">
                    <h3>⬆️ Upstream (${upstream.length})</h3>
                    ${upstream.length > 0 ? `
                        <table class="data-table">
                            <thead><tr><th>Type</th><th>Title</th></tr></thead>
                            <tbody>${upstream.map(u => `
                                <tr><td><span class="badge">${u.type}</span></td><td>${escHtml(u.title)}</td></tr>`).join('')}
                            </tbody>
                        </table>` : '<p style="color:var(--sap-text-secondary)">No upstream links.</p>'}
                </div>
                <div class="card" style="margin-top:16px">
                    <h3>⬇️ Downstream (${downstream.length})</h3>
                    ${downstream.length > 0 ? `
                        <table class="data-table">
                            <thead><tr><th>Type</th><th>Title</th></tr></thead>
                            <tbody>${downstream.map(d => `
                                <tr><td><span class="badge">${d.type}</span></td><td>${escHtml(d.title)}</td></tr>`).join('')}
                            </tbody>
                        </table>` : '<p style="color:var(--sap-text-secondary)">No downstream links.</p>'}
                </div>
                <div class="card" style="margin-top:16px">
                    <h3>📊 Links Summary</h3>
                    <dl class="detail-list">
                        ${Object.entries(chain.links_summary || {}).map(([k, v]) =>
                            `<dt>${k}</dt><dd>${v}</dd>`).join('')}
                    </dl>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div class="card" style="margin-top:12px"><p>Could not load traceability data.</p></div>`;
        }
    }

    // ── Stats Modal ──────────────────────────────────────────────────────
    async function showStats() {
        try {
            let stats;
            try {
                stats = await API.get(`/programs/${programId}/backlog/stats`);
            } catch (err) {
                stats = _buildBacklogStatsFallback();
            }

            const cfgStats = _buildConfigStats();

            const typeRows = Object.entries(stats.by_wricef_type || {}).map(([k, v]) => {
                const w = WRICEF[k] || WRICEF.enhancement;
                return `<tr><td>${w.icon} ${w.label}</td><td>${v}</td></tr>`;
            }).join('');
            const statusRows = Object.entries(stats.by_status || {}).map(([k, v]) =>
                `<tr><td><span class="badge badge-${k}">${STATUS_LABELS[k] || k}</span></td><td>${v}</td></tr>`
            ).join('');

            const cfgStatusRows = Object.entries(cfgStats.by_status).map(([k, v]) =>
                `<tr><td><span class="badge badge-${k}">${STATUS_LABELS[k] || k}</span></td><td>${v}</td></tr>`
            ).join('');
            const cfgPriorityRows = Object.entries(cfgStats.by_priority).map(([k, v]) =>
                `<tr><td><span class="badge badge-${k}">${k}</span></td><td>${v}</td></tr>`
            ).join('');

            App.openModal(`
                <h2>Backlog Statistics</h2>
                <div class="detail-grid" style="margin-top:16px">
                    <div>
                        <h4>WRICEF — By Type</h4>
                        <table class="data-table"><thead><tr><th>Type</th><th>Count</th></tr></thead>
                        <tbody>${typeRows || '<tr><td colspan="2">No data</td></tr>'}</tbody></table>
                    </div>
                    <div>
                        <h4>WRICEF — By Status</h4>
                        <table class="data-table"><thead><tr><th>Status</th><th>Count</th></tr></thead>
                        <tbody>${statusRows || '<tr><td colspan="2">No data</td></tr>'}</tbody></table>
                    </div>
                </div>
                <div style="margin-top:16px">
                    <p><strong>WRICEF Total Items:</strong> ${stats.total_items || 0}</p>
                    <p><strong>Total Story Points:</strong> ${stats.total_story_points || 0}</p>
                    <p><strong>Estimated Hours:</strong> ${stats.total_estimated_hours || 0}</p>
                    <p><strong>Actual Hours:</strong> ${stats.total_actual_hours || 0}</p>
                </div>
                <div class="detail-grid" style="margin-top:24px">
                    <div>
                        <h4>Config — By Status</h4>
                        <table class="data-table"><thead><tr><th>Status</th><th>Count</th></tr></thead>
                        <tbody>${cfgStatusRows || '<tr><td colspan="2">No data</td></tr>'}</tbody></table>
                    </div>
                    <div>
                        <h4>Config — By Priority</h4>
                        <table class="data-table"><thead><tr><th>Priority</th><th>Count</th></tr></thead>
                        <tbody>${cfgPriorityRows || '<tr><td colspan="2">No data</td></tr>'}</tbody></table>
                    </div>
                </div>
                <div style="margin-top:16px">
                    <p><strong>Config Total Items:</strong> ${cfgStats.total}</p>
                </div>
                <div style="text-align:right;margin-top:20px">
                    <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
                </div>
            `);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function _buildBacklogStatsFallback() {
        const byType = {};
        const byStatus = {};
        let totalPoints = 0;
        let totalEstimated = 0;
        let totalActual = 0;

        items.forEach(i => {
            byType[i.wricef_type] = (byType[i.wricef_type] || 0) + 1;
            byStatus[i.status] = (byStatus[i.status] || 0) + 1;
            totalPoints += i.story_points || 0;
            totalEstimated += i.estimated_hours || 0;
            totalActual += i.actual_hours || 0;
        });

        return {
            total_items: items.length,
            total_story_points: totalPoints,
            total_estimated_hours: totalEstimated,
            total_actual_hours: totalActual,
            by_wricef_type: byType,
            by_status: byStatus,
        };
    }

    function _buildConfigStats() {
        const byStatus = {};
        const byPriority = {};
        configItems.forEach(ci => {
            byStatus[ci.status] = (byStatus[ci.status] || 0) + 1;
            byPriority[ci.priority] = (byPriority[ci.priority] || 0) + 1;
        });
        return {
            total: configItems.length,
            by_status: byStatus,
            by_priority: byPriority,
        };
    }

    function showCreateSelector() {
        App.openModal(`
            <h2>Create Item</h2>
            <p style="color:var(--sap-text-secondary);margin-top:4px">Select what you want to create.</p>
            <div style="display:grid;gap:10px;margin-top:16px">
                <button class="btn btn-primary" onclick="BacklogView.createWricefFromSelector()">WRICEF Item</button>
                <button class="btn btn-secondary" onclick="BacklogView.createConfigFromSelector()">Config Item</button>
            </div>
        `);
    }

    function createWricefFromSelector() {
        App.closeModal();
        showCreateModal();
    }

    function createConfigFromSelector() {
        App.closeModal();
        showCreateConfigModal();
    }

    // ── Create Item Modal ────────────────────────────────────────────────
    function showCreateModal() {
        _showItemForm(null);
    }

    function showEditModal() {
        if (!currentItem) return;
        _showItemForm(currentItem);
    }

    async function _showItemForm(item) {
        const isEdit = !!item;
        const title = isEdit ? 'Edit Backlog Item' : 'New Backlog Item';
        const members = await TeamMemberPicker.fetchMembers(programId);
        const assignedHtml = TeamMemberPicker.renderSelect('biAssigned', members, item?.assigned_to_id || item?.assigned_to || '', { cssClass: 'form-input' });

        App.openModal(`
            <h2>${title}</h2>
            <div style="max-height:70vh;overflow-y:auto;padding-right:8px">
                <div class="form-row">
                    <div class="form-group"><label>Title *</label><input id="biTitle" class="form-input" value="${escHtml(item?.title || '')}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>WRICEF Type *</label>
                        <select id="biType" class="form-input">
                            ${Object.entries(WRICEF).map(([k, v]) =>
                                `<option value="${k}" ${item?.wricef_type === k ? 'selected' : ''}>${v.icon} ${v.label}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Code</label><input id="biCode" class="form-input" placeholder="e.g. ENH-FI-001" value="${escHtml(item?.code || '')}"></div>
                </div>
                <div class="form-group"><label>Description</label><textarea id="biDesc" class="form-input" rows="3">${escHtml(item?.description || '')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Module</label>
                        <select id="biModule" class="form-input">
                            <option value="">—</option>
                            ${['FI','CO','MM','SD','PP','PM','QM','HCM','PS','WM','EWM','BTP','Basis','ABAP','Other'].map(m =>
                                `<option value="${m}" ${item?.module === m ? 'selected' : ''}>${m}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Sub Type</label><input id="biSubType" class="form-input" placeholder="e.g. BAdI, RFC, ALV" value="${escHtml(item?.sub_type || '')}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Priority</label>
                        <select id="biPriority" class="form-input">
                            ${['low','medium','high','critical'].map(p =>
                                `<option value="${p}" ${(item?.priority || 'medium') === p ? 'selected' : ''}>${p}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Complexity</label>
                        <select id="biComplexity" class="form-input">
                            ${['low','medium','high','very_high'].map(c =>
                                `<option value="${c}" ${(item?.complexity || 'medium') === c ? 'selected' : ''}>${c}</option>`
                            ).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Story Points</label><input id="biSP" type="number" class="form-input" value="${item?.story_points || ''}"></div>
                    <div class="form-group"><label>Estimated Hours</label><input id="biEstH" type="number" step="0.5" class="form-input" value="${item?.estimated_hours || ''}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Assigned To</label>${assignedHtml}</div>
                    <div class="form-group"><label>Sprint</label>
                        <select id="biSprint" class="form-input">
                            <option value="">Unassigned</option>
                            ${sprints.map(s => `<option value="${s.id}" ${item?.sprint_id === s.id ? 'selected' : ''}>${escHtml(s.name)}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Transaction Code</label><input id="biTCode" class="form-input" value="${escHtml(item?.transaction_code || '')}"></div>
                    <div class="form-group"><label>Package</label><input id="biPkg" class="form-input" value="${escHtml(item?.package || '')}"></div>
                </div>
                <div class="form-group"><label>Acceptance Criteria</label><textarea id="biAC" class="form-input" rows="2">${escHtml(item?.acceptance_criteria || '')}</textarea></div>
                <div class="form-group"><label>Technical Notes</label><textarea id="biTechNotes" class="form-input" rows="2">${escHtml(item?.technical_notes || '')}</textarea></div>
                <div class="form-group"><label>Notes</label><textarea id="biNotes" class="form-input" rows="2">${escHtml(item?.notes || '')}</textarea></div>
            </div>
            <div style="text-align:right;margin-top:16px">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="BacklogView.saveItem(${isEdit ? item.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `);
    }

    async function saveItem(itemId) {
        const payload = {
            title: document.getElementById('biTitle').value.trim(),
            wricef_type: document.getElementById('biType').value,
            code: document.getElementById('biCode').value.trim(),
            description: document.getElementById('biDesc').value.trim(),
            module: document.getElementById('biModule').value,
            sub_type: document.getElementById('biSubType').value.trim(),
            priority: document.getElementById('biPriority').value,
            complexity: document.getElementById('biComplexity').value,
            story_points: parseInt(document.getElementById('biSP').value) || null,
            estimated_hours: parseFloat(document.getElementById('biEstH').value) || null,
            assigned_to: document.getElementById('biAssigned').value.trim() || null,
            assigned_to_id: document.getElementById('biAssigned').value.trim() || null,
            sprint_id: parseInt(document.getElementById('biSprint').value) || null,
            transaction_code: document.getElementById('biTCode').value.trim(),
            package: document.getElementById('biPkg').value.trim(),
            acceptance_criteria: document.getElementById('biAC').value.trim(),
            technical_notes: document.getElementById('biTechNotes').value.trim(),
            notes: document.getElementById('biNotes').value.trim(),
        };

        if (!payload.title) { App.toast('Title is required', 'error'); return; }

        try {
            if (itemId) {
                await API.put(`/backlog/${itemId}`, payload);
                App.toast('Backlog item updated', 'success');
            } else {
                await API.post(`/programs/${programId}/backlog`, payload);
                App.toast('Backlog item created', 'success');
            }
            App.closeModal();
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Move Modal ───────────────────────────────────────────────────────
    const TRANSITIONS = {
        'new':       ['design', 'cancelled'],
        'design':    ['build', 'blocked', 'cancelled'],
        'build':     ['test', 'blocked', 'cancelled'],
        'test':      ['deploy', 'design', 'blocked'],
        'deploy':    ['closed', 'blocked'],
        'blocked':   ['new', 'design', 'build', 'test'],
        'closed':    [],
        'cancelled': [],
    };

    function showMoveModal() {
        if (!currentItem) return;
        const allowed = TRANSITIONS[currentItem.status] || [];
        if (allowed.length === 0) {
            App.toast('This item is in a terminal state and cannot be moved', 'error');
            return;
        }
        App.openModal(`
            <h2>Move Item</h2>
            <div class="form-group"><label>Status</label>
                <select id="moveStatus" class="form-input">
                    ${allowed.map(k =>
                        `<option value="${k}">${STATUS_LABELS[k] || k}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group"><label>Sprint</label>
                <select id="moveSprint" class="form-input">
                    <option value="">Unassigned</option>
                    ${sprints.map(s => `<option value="${s.id}" ${currentItem.sprint_id === s.id ? 'selected' : ''}>${escHtml(s.name)}</option>`).join('')}
                </select>
            </div>
            <div style="text-align:right;margin-top:16px">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="BacklogView.doMove()">Move</button>
            </div>
        `);
    }

    async function doMove() {
        try {
            const result = await API.patch(`/backlog/${currentItem.id}/move`, {
                status: document.getElementById('moveStatus').value,
                sprint_id: parseInt(document.getElementById('moveSprint').value) || null,
            });
            App.closeModal();
            // Show side-effect info
            const fx = result._side_effects || {};
            if (fx.functional_spec_created) {
                App.toast('Moved to Design — Draft FS created automatically', 'success');
            } else if (fx.unit_tests_created) {
                App.toast('Moved to Test — Unit test cases generated', 'success');
            } else {
                App.toast('Item moved', 'success');
            }
            // Re-open detail with specs to show FS/TS
            await openDetail(currentItem.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteItem(id) {
        if (!confirm('Delete this backlog item?')) return;
        try {
            await API.delete(`/backlog/${id}`);
            App.toast('Item deleted', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Sprint CRUD ──────────────────────────────────────────────────────
    function showCreateSprintModal() { _showSprintForm(null); }

    async function showEditSprintModal(id) {
        const sprint = sprints.find(s => s.id === id);
        if (sprint) _showSprintForm(sprint);
    }

    function _showSprintForm(sprint) {
        const isEdit = !!sprint;
        App.openModal(`
            <h2>${isEdit ? 'Edit Sprint' : 'New Sprint'}</h2>
            <div class="form-group"><label>Name *</label><input id="spName" class="form-input" value="${escHtml(sprint?.name || '')}"></div>
            <div class="form-group"><label>Goal</label><textarea id="spGoal" class="form-input" rows="2">${escHtml(sprint?.goal || '')}</textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Status</label>
                    <select id="spStatus" class="form-input">
                        ${['planning','active','completed','cancelled'].map(s =>
                            `<option value="${s}" ${(sprint?.status || 'planning') === s ? 'selected' : ''}>${s}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="form-group"><label>Capacity (SP)</label><input id="spCap" type="number" class="form-input" value="${sprint?.capacity_points || ''}"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Start Date</label><input id="spStart" type="date" class="form-input" value="${sprint?.start_date || ''}"></div>
                <div class="form-group"><label>End Date</label><input id="spEnd" type="date" class="form-input" value="${sprint?.end_date || ''}"></div>
            </div>
            ${isEdit ? `<div class="form-group"><label>Velocity (actual)</label><input id="spVel" type="number" class="form-input" value="${sprint?.velocity || ''}"></div>` : ''}
            <div style="text-align:right;margin-top:16px">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="BacklogView.saveSprint(${isEdit ? sprint.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `);
    }

    async function saveSprint(sprintId) {
        const payload = {
            name: document.getElementById('spName').value.trim(),
            goal: document.getElementById('spGoal').value.trim(),
            status: document.getElementById('spStatus').value,
            capacity_points: parseInt(document.getElementById('spCap').value) || null,
            start_date: document.getElementById('spStart').value || null,
            end_date: document.getElementById('spEnd').value || null,
        };
        const velEl = document.getElementById('spVel');
        if (velEl) payload.velocity = parseInt(velEl.value) || null;

        if (!payload.name) { App.toast('Sprint name is required', 'error'); return; }

        try {
            if (sprintId) {
                await API.put(`/sprints/${sprintId}`, payload);
                App.toast('Sprint updated', 'success');
            } else {
                await API.post(`/programs/${programId}/sprints`, payload);
                App.toast('Sprint created', 'success');
            }
            App.closeModal();
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteSprint(id) {
        if (!confirm('Delete this sprint? Items will be unassigned.')) return;
        try {
            await API.delete(`/sprints/${id}`);
            App.toast('Sprint deleted', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Helpers ──────────────────────────────────────────────────────────
    function escHtml(s) {
        const el = document.createElement('span');
        el.textContent = s || '';
        return el.innerHTML;
    }

    // ── Spec Actions (FS/TS) ─────────────────────────────────────────────

    async function updateSpecStatus(specType, specId, newStatus) {
        const endpoint = specType === 'fs'
            ? `/functional-specs/${specId}`
            : `/technical-specs/${specId}`;
        const label = specType === 'fs' ? 'Functional Spec' : 'Technical Spec';

        try {
            const result = await API.put(endpoint, { status: newStatus });
            const fx = result._side_effects || {};

            if (fx.technical_spec_created) {
                App.toast(`${label} approved — Draft TS created automatically`, 'success');
            } else if (fx.backlog_item_moved_to_build) {
                App.toast(`${label} approved — Item moved to Build`, 'success');
            } else {
                App.toast(`${label} status → ${newStatus}`, 'success');
            }

            // Re-fetch item with specs and re-render detail
            await openDetail(currentItem.id);
            switchDetailTab('specs');
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function downloadSpec(specType, specId, title) {
        const item = currentItem;
        const fs = item.functional_spec;
        const spec = specType === 'fs' ? fs : (fs ? fs.technical_spec : null);
        if (!spec || !spec.content) {
            App.toast('No content to download', 'error');
            return;
        }

        const filename = `${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`;
        const blob = new Blob([spec.content], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    async function editSpec(specType, specId) {
        const item = currentItem;
        const fs = item.functional_spec;
        const spec = specType === 'fs' ? fs : (fs ? fs.technical_spec : null);
        if (!spec) return;

        const label = specType === 'fs' ? 'Functional Specification' : 'Technical Specification';

        App.openModal(`
            <h2>Edit ${label}</h2>
            <div class="form-group"><label>Title</label>
                <input id="specTitle" class="form-input" value="${escHtml(spec.title)}">
            </div>
            <div class="form-group"><label>Author</label>
                <input id="specAuthor" class="form-input" value="${escHtml(spec.author || '')}">
            </div>
            <div class="form-group"><label>Reviewer</label>
                <input id="specReviewer" class="form-input" value="${escHtml(spec.reviewer || '')}">
            </div>
            <div class="form-group"><label>Content (Markdown)</label>
                <textarea id="specContent" class="form-input" rows="15" style="font-family:monospace;font-size:13px">${escHtml(spec.content || '')}</textarea>
            </div>
            <div style="text-align:right;margin-top:16px">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="BacklogView.saveSpec('${specType}', ${specId})">Save</button>
            </div>
        `);
    }

    async function saveSpec(specType, specId) {
        const endpoint = specType === 'fs'
            ? `/functional-specs/${specId}`
            : `/technical-specs/${specId}`;

        const payload = {
            title: document.getElementById('specTitle').value,
            author: document.getElementById('specAuthor').value,
            reviewer: document.getElementById('specReviewer').value,
            content: document.getElementById('specContent').value,
        };

        try {
            await API.put(endpoint, payload);
            App.toast('Spec saved', 'success');
            App.closeModal();
            await openDetail(currentItem.id);
            switchDetailTab('specs');
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // Public API
    return {
        render, switchTab, applyListFilter, setListSearch, onListFilterChange,
        setConfigSearch, onConfigFilterChange, applyConfigFilter,
        showCreateModal, showCreateSelector, createWricefFromSelector,
        createConfigFromSelector, showEditModal, saveItem,
        openDetail, deleteItem, switchDetailTab,
        showMoveModal, doMove,
        showStats,
        showCreateSprintModal, showEditSprintModal, saveSprint, deleteSprint,
        showCreateConfigModal, showEditConfigModal, saveConfigItem, deleteConfigItem,
        openConfigDetail,
        updateSpecStatus, downloadSpec, editSpec, saveSpec,
        _generateSpecs,
    };
})();
