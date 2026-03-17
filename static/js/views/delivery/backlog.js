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
    let currentConfigItem = null;
    let specEditorState = null;
    let teamMembers = [];
    let programId = null;
    let currentTab = 'board'; // board | list | sprints | config
    let currentDetailTab = 'overview';
    let currentDetailMode = 'view';
    let currentDetailReturnTab = 'overview';
    let recentDetailChangeFields = [];
    let recentDetailChangeLabels = [];
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

    const STATUS_HELP_TEXT = {
        new: 'Item yeni alindi; analiz ve cozum tasarimi henuz baslamadi.',
        design: 'Cozum yaklasimi netlesiyor; functional spec ve kapsam bu asamada olgunlasir.',
        build: 'Gelistirme veya customizing isi aktif olarak yurutuluyor.',
        test: 'Cikti test hazirligina veya dogrulama asamasina gecti.',
        deploy: 'Tasimaya ve yayin oncesi hazirliklara gecildi.',
        closed: 'Is tamamlandi ve kapanis kriterleri saglandi.',
        blocked: 'Ilerleme bir bagimlilik veya engel nedeniyle durdu.',
        cancelled: 'Is kapsamdan cikarildi veya artik takip edilmeyecek.',
    };

    const STATUS_FLOW_ORDER = ['new', 'design', 'build', 'test', 'deploy', 'closed'];
    const STATUS_EXCEPTION_ORDER = ['blocked', 'cancelled'];

    function _deliveryNav(hub, current) {
        return typeof DeliveryHubUI !== 'undefined' && DeliveryHubUI?.nav
            ? DeliveryHubUI.nav(hub, current)
            : '';
    }

    function _statusHelpText(status) {
        return STATUS_HELP_TEXT[status] || 'Selected status updates the current delivery stage of the item.';
    }

    function _setCollections(boardRes, sprintRes, configRes) {
        boardData = boardRes || { columns: {}, summary: { total_items: 0, total_points: 0, done_points: 0, completion_pct: 0 } };
        sprints = Array.isArray(sprintRes) ? sprintRes : (sprintRes?.items || []);
        configItems = Array.isArray(configRes) ? configRes : (configRes?.items || []);

        items = [];
        Object.values(boardData.columns || {}).forEach((columnItems) => {
            if (Array.isArray(columnItems)) items.push(...columnItems);
        });
    }

    function _hasBacklogShell() {
        return Boolean(document.getElementById('backlogContent'));
    }

    async function _ensureTeamMembers() {
        teamMembers = await TeamMemberPicker.fetchMembers(programId);
        return teamMembers;
    }

    async function _refreshCollections({ rerender = true } = {}) {
        const [boardRes, sprintRes, configRes] = await Promise.all([
            API.get(`/programs/${programId}/backlog/board`),
            API.get(`/programs/${programId}/sprints`),
            API.get(`/programs/${programId}/config-items`),
        ]);
        _setCollections(boardRes, sprintRes, configRes);
        if (rerender && _hasBacklogShell()) renderCurrentTab();
    }

    // ── Sprint Velocity Spark Bar (UI-S05-T05) ────────────────────────────
    function _sparkBar(values, color = '#0070f2', height = 28) {
        if (!values || values.length === 0) return '';
        const max = Math.max(...values, 1);
        const barW = 18;
        const gap  = 3;
        const w    = values.length * (barW + gap) - gap;
        const bars = values.map((v, i) => {
            const h = Math.max(2, Math.round(v / max * height));
            const y = height - h;
            return `<rect x="${i * (barW + gap)}" y="${y}" width="${barW}" height="${h}" rx="2"
                fill="${color}" opacity="${i === values.length - 1 ? 1 : 0.45}"/>`;
        }).join('');
        return `<svg width="${w}" height="${height}" viewBox="0 0 ${w} ${height}" style="overflow:visible;vertical-align:middle">${bars}</svg>`;
    }

    // ── Filter Chip Bar (UI-S05-T02) ─────────────────────────────────────
    const _filterKeyLabel = (key) => ({ status: 'Status', priority: 'Priority', wricef_type: 'Type', sprint: 'Sprint', assignee: 'Assignee', module: 'Module' })[key] || key;

    function _renderFilterBar(filters, clearFn, clearAllFn) {
        const active = Object.entries(filters).filter(([, v]) => v && (Array.isArray(v) ? v.length > 0 : v !== 'all'));
        if (active.length === 0) return '';

        const chips = active.flatMap(([k, v]) => {
            const vals = Array.isArray(v) ? v : [v];
            return vals.map(val => `
                <span class="pg-filter-chip">
                    <span class="pg-filter-chip__key">${_filterKeyLabel(k)}</span>
                    <span class="pg-filter-chip__val">${val}</span>
                    <button class="pg-filter-chip__clear" onclick="${clearFn}('${k}','${val}')" aria-label="Remove filter">×</button>
                </span>
            `);
        }).join('');

        return `
            <div class="pg-filter-bar">
                <div class="pg-filter-bar__chips">${chips}</div>
                <div class="pg-filter-bar__actions">
                    <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="${clearAllFn}()">Clear All</button>
                </div>
            </div>
        `;
    }

    // ── Main render ──────────────────────────────────────────────────────
    async function render() {
        currentItem = null;
        specEditorState = null;
        currentDetailTab = 'overview';
        const prog = App.getActiveProgram();
        programId = prog ? prog.id : null;
        const main = document.getElementById('mainContent');

        if (!programId) {
            main.innerHTML = PGEmptyState.html({ icon: 'backlog', title: 'Backlog', description: 'Select a program to access the development backlog.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{label:'Programs',onclick:'App.navigate("programs")'},{label:'Backlog'}])}
                <div class="backlog-header">
                    <div>
                        <h2 class="pg-view-title">Backlog</h2>
                        <p class="backlog-header__subtitle">Development objects, config items, and sprint planning</p>
                    </div>
                    <div class="backlog-header__actions">
                        ${ExpUI.actionButton({ label: 'Stats', variant: 'secondary', size: 'md', onclick: 'BacklogView.showStats()' })}
                        ${ExpUI.actionButton({ label: 'AI WRICEF Spec', variant: 'secondary', size: 'md', onclick: 'BacklogView.showAIWricefSpecModal()' })}
                        ${ExpUI.actionButton({ label: '+ New Item', variant: 'primary', size: 'md', onclick: 'BacklogView.showCreateSelector()' })}
                    </div>
                </div>
            </div>
            ${typeof DeliveryHubUI !== 'undefined' && DeliveryHubUI?.nav
                ? DeliveryHubUI.nav('build', 'backlog')
                : _deliveryNav('build', 'backlog')}
            <div class="tabs backlog-tabs-shell">
                <button class="tab-btn ${currentTab === 'board' ? 'active' : ''}" data-tab="board" onclick="BacklogView.switchTab('board')">Kanban Board</button>
                <button class="tab-btn ${currentTab === 'list' ? 'active' : ''}" data-tab="list" onclick="BacklogView.switchTab('list')">WRICEF List</button>
                <button class="tab-btn ${currentTab === 'config' ? 'active' : ''}" data-tab="config" onclick="BacklogView.switchTab('config')">Config Items</button>
                <button class="tab-btn ${currentTab === 'sprints' ? 'active' : ''}" data-tab="sprints" onclick="BacklogView.switchTab('sprints')">Sprints</button>
            </div>
            <div id="backlogContent">
                <div class="backlog-content-loading"><div class="spinner"></div></div>
            </div>`;

        await loadData();
    }

    function _getSelectedProgramId() {
        const prog = App.getActiveProgram();
        return prog ? prog.id : null;
    }

    async function loadData() {
        try {
            await _refreshCollections();
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
                            ${(boardData.columns[status] || []).length === 0
                                ? PGEmptyState.html({ icon: 'build', title: 'No items in this column' })
                                : (boardData.columns[status] || []).map(item => _renderKanbanCard(item)).join('')
                            }
                        </div>
                    </div>
                `).join('')}
            </div>`;
    }

    function _renderKanbanCard(item) {
        const w = WRICEF[item.wricef_type] || WRICEF.enhancement;
        const linkCount = (item.explore_requirement_id ? 1 : 0) +
                          (item.functional_spec ? 1 : 0) +
                          (item.technical_spec ? 1 : 0);
        return `
            <div class="kanban-card" data-id="${item.id}" onclick="BacklogView.openDetail(${item.id})">
                <div class="kanban-card__header">
                    <span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label[0]}</span>
                    ${PGStatusRegistry.badge(item.priority)}
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
            c.innerHTML = PGEmptyState.html({ icon: 'backlog', title: 'No backlog items yet', description: 'Create your first WRICEF item to build the development backlog.', action: { label: '+ New Item', onclick: 'BacklogView.showCreateModal()' } });
            return;
        }

        c.innerHTML = `
            <div id="blChipBar"></div>
            <div id="blFilterBar" class="backlog-filter-bar"></div>
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

        const chipBar = document.getElementById('blChipBar');
        if (chipBar) chipBar.innerHTML = _renderFilterBar(_listFilters, 'BacklogView.clearListFilter', 'BacklogView.clearAllListFilters');

        const countEl = document.getElementById('blItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${items.length}`;

        const tableEl = document.getElementById('blListTable');
        if (!tableEl) return;
        if (filtered.length === 0) {
            tableEl.innerHTML = '<div class="empty-state backlog-empty"><p>No items match your filters.</p></div>';
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
            actionsHtml: '<span class="backlog-filter-count" id="blItemCount"></span>',
        });
    }

    function setListSearch(val) {
        _listSearch = val;
        applyListFilter();
    }

    function clearListFilter(key, val) {
        if (!_listFilters[key]) return;
        if (Array.isArray(_listFilters[key])) {
            _listFilters[key] = _listFilters[key].filter(v => v !== val);
            if (_listFilters[key].length === 0) delete _listFilters[key];
        } else {
            delete _listFilters[key];
        }
        renderListFilterBar();
        applyListFilter();
    }

    function clearAllListFilters() {
        _listFilters = {};
        renderListFilterBar();
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
        let html = `<table class="data-table backlog-table">
            <thead><tr>
                <th class="backlog-table__col--type">Type</th>
                <th class="backlog-table__col--code">Code</th>
                <th>Title</th>
                <th class="backlog-table__col--module">Module</th>
                <th class="backlog-table__col--status">Status</th>
                <th class="backlog-table__col--priority">Priority</th>
                <th class="backlog-table__col--sp">SP</th>
                <th class="backlog-table__col--assigned">Assigned</th>
                <th class="backlog-table__col--actions"></th>
            </tr></thead><tbody>`;

        list.forEach(i => {
            const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
            const linkCount = (i.explore_requirement_id ? 1 : 0) + (i.functional_spec ? 1 : 0) + (i.technical_spec ? 1 : 0);

            html += `<tr class="backlog-table__row" onclick="BacklogView.openDetail(${i.id})">
                <td><span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label[0]}</span></td>
                <td><code class="backlog-code">${escHtml(i.code || '—')}</code></td>
                <td>
                    <span class="backlog-title">${escHtml(i.title)}</span>
                    ${linkCount > 0 ? `<span class="backlog-link-count">🔗${linkCount}</span>` : ''}
                </td>
                <td><span class="backlog-cell-copy">${escHtml(i.module || '—')}</span></td>
                <td>${PGStatusRegistry.badge(i.status, { label: STATUS_LABELS[i.status] || i.status || '—' })}</td>
                <td>${PGStatusRegistry.badge(i.priority)}</td>
                <td class="backlog-sp">${i.story_points || '—'}</td>
                <td><span class="backlog-cell-copy">${escHtml(i.assigned_to || '—')}</span></td>
                <td class="backlog-actions-right" onclick="event.stopPropagation()">
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
            <div class="backlog-toolbar-right">
                ${ExpUI.actionButton({ label: '+ New Sprint', variant: 'primary', size: 'sm', onclick: 'BacklogView.showCreateSprintModal()' })}
            </div>
            ${sprints.length === 0 ? PGEmptyState.html({ icon: 'backlog', title: 'No sprints yet', description: 'Create sprints to plan and group your backlog items into iterations.' }) :
                sprints.map(s => {
                    const sprintItems = items.filter(i => i.sprint_id === s.id);
                    const totalPts = sprintItems.reduce((sum, i) => sum + (i.story_points || 0), 0);
                    const donePts = sprintItems.filter(i => i.status === 'closed').reduce((sum, i) => sum + (i.story_points || 0), 0);
                    return `
                        <div class="card sprint-card backlog-sprint-card">
                            <div class="card-header">
                                <div>
                                    <h3>${escHtml(s.name)}</h3>
                                    ${PGStatusRegistry.badge(s.status)}
                                    ${s.start_date ? `<span class="backlog-sprint-date">${s.start_date} → ${s.end_date || '?'}</span>` : ''}
                                </div>
                                <div class="backlog-sprint-header-actions">
                                    <button class="btn-icon" onclick="BacklogView.showEditSprintModal(${s.id})" title="Edit">
                                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
                                    </button>
                                    <button class="btn-icon btn-icon--danger" onclick="BacklogView.deleteSprint(${s.id})" title="Delete">
                                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
                                    </button>
                                </div>
                            </div>
                            ${s.goal ? `<p class="backlog-sprint-goal">${escHtml(s.goal)}</p>` : ''}
                            <div class="sprint-metrics">
                                <span><strong>${sprintItems.length}</strong> items</span>
                                <span><strong>${totalPts}</strong> points</span>
                                <span><strong>${donePts}</strong> done</span>
                                ${s.capacity_points ? `<span><strong>${s.capacity_points}</strong> capacity</span>` : ''}
                                ${s.velocity != null ? `<span><strong>${s.velocity}</strong> velocity</span>` : ''}
                            </div>
                            ${totalPts > 0 ? `
                            <div class="backlog-sprint-velocity">
                                <span class="backlog-sprint-hint">Velocity</span>
                                ${_sparkBar([donePts, totalPts - donePts > 0 ? totalPts - donePts : 0].concat(s.velocity ? [s.velocity] : []), '#0070f2', 24)}
                                ${s.capacity_points ? `<span class="backlog-sprint-hint">${Math.round(totalPts / s.capacity_points * 100)}% capacity</span>` : ''}
                            </div>` : ''}
                            ${sprintItems.length > 0 ? `
                                <table class="data-table backlog-table--spaced">
                                    <thead><tr><th>Type</th><th>Code</th><th>Title</th><th>Status</th><th>SP</th></tr></thead>
                                    <tbody>
                                        ${sprintItems.map(i => {
                                            const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
                                            return `<tr class="backlog-table__row" onclick="BacklogView.openDetail(${i.id})">
                                                <td><span class="wricef-badge" style="background:${w.color}">${w.icon}</span></td>
                                                <td>${escHtml(i.code || '—')}</td>
                                                <td>${escHtml(i.title)}</td>
                                                <td>${PGStatusRegistry.badge(i.status, { label: STATUS_LABELS[i.status] || i.status })}</td>
                                                <td>${i.story_points || '—'}</td>
                                            </tr>`;
                                        }).join('')}
                                    </tbody>
                                </table>` : '<p class="backlog-table-empty">No items assigned to this sprint.</p>'}
                        </div>`;
                }).join('')}
            <!-- Unassigned backlog -->
            <div class="card backlog-config-card">
                <div class="card-header"><h3>Unassigned Backlog</h3></div>
                ${(() => {
                    const unassigned = items.filter(i => !i.sprint_id);
                    if (unassigned.length === 0) return '<p class="backlog-table-empty">All items are assigned to sprints.</p>';
                    return `<table class="data-table"><thead><tr><th>Type</th><th>Code</th><th>Title</th><th>Status</th><th>SP</th></tr></thead><tbody>
                        ${unassigned.map(i => {
                            const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
                            return `<tr class="backlog-table__row" onclick="BacklogView.openDetail(${i.id})">
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
            ${configItems.length === 0 ? PGEmptyState.html({ icon: 'backlog', title: 'No config items yet', description: 'Create configuration items to track SAP customizing changes.' }) : `
            <div id="ciFilterBar" class="backlog-filter-bar"></div>
            <div id="ciListTable"></div>`}`;

        if (configItems.length > 0) {
            renderConfigFilterBar();
            applyConfigFilter();
        }

        c.insertAdjacentHTML('beforeend', `
            <div class="backlog-toolbar-right">
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
            actionsHtml: '<span class="backlog-filter-count" id="ciItemCount"></span>',
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
            tableEl.innerHTML = '<div class="empty-state backlog-empty"><p>No items match your filters.</p></div>';
            return;
        }

        tableEl.innerHTML = _renderConfigListTable(filtered);
    }

    function _renderConfigListTable(list) {
        let html = `<table class="data-table backlog-table">
            <thead><tr>
                <th class="backlog-table__col--code">Code</th>
                <th>Title</th>
                <th class="backlog-table__col--module">Module</th>
                <th>Config Key</th>
                <th class="backlog-table__col--status">Status</th>
                <th class="backlog-table__col--priority">Priority</th>
                <th class="backlog-table__col--assigned">Assigned</th>
                <th class="backlog-table__col--actions"></th>
            </tr></thead><tbody>`;

        list.forEach(ci => {
            html += `<tr class="backlog-table__row" onclick="BacklogView.openConfigDetail(${ci.id})">
                <td><code class="backlog-code">${escHtml(ci.code || '—')}</code></td>
                <td><span class="backlog-title">${escHtml(ci.title)}</span></td>
                <td><span class="backlog-cell-copy">${escHtml(ci.module || '—')}</span></td>
                <td><span class="backlog-cell-copy">${escHtml(ci.config_key || '—')}</span></td>
                <td>${PGStatusRegistry.badge(ci.status, { label: STATUS_LABELS[ci.status] || ci.status || '—' })}</td>
                <td>${PGStatusRegistry.badge(ci.priority)}</td>
                <td><span class="backlog-cell-copy">${escHtml(ci.assigned_to || '—')}</span></td>
                <td class="backlog-actions-right" onclick="event.stopPropagation()">
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
            <div class="backlog-modal-actions">
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
            assigned_to: TeamMemberPicker.selectedMemberName('ciAssigned') || null,
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
        _openConfirmModal('Delete Config Item', 'Delete this config item?', `BacklogView.deleteConfigItemConfirmed(${id})`);
    }

    async function deleteConfigItemConfirmed(id) {
        try {
            await API.delete(`/config-items/${id}`);
            App.closeModal();
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
        currentConfigItem = ci;

        const fs = ci.functional_spec;
        const ts = fs ? fs.technical_spec : null;
        const main = document.getElementById('mainContent');
        const allowedMoves = TRANSITIONS[ci.status] || [];

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{label:'Backlog',onclick:'BacklogView.render()'},{label:escHtml(ci.code||ci.title)}])}
                <div class="backlog-config-header">
                    <div class="backlog-config-header__title">
                        <h2 class="pg-view-title">${escHtml(ci.code || '')} ${escHtml(ci.title)}</h2>
                        ${PGStatusRegistry.badge(ci.status, { label: STATUS_LABELS[ci.status] || ci.status })}
                    </div>
                    <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="BacklogView.showEditConfigModal(${ci.id})">Edit</button>
                </div>
            </div>

            <div class="detail-grid">
                <div class="detail-section">
                    <h3>Classification</h3>
                    <dl class="detail-list">
                        <dt>Module</dt><dd>${escHtml(ci.module || '—')}</dd>
                        <dt>Config Key</dt><dd>${escHtml(ci.config_key || '—')}</dd>
                        <dt>Priority</dt><dd>${PGStatusRegistry.badge(ci.priority)}</dd>
                        <dt>Assigned To</dt><dd>${escHtml(ci.assigned_to || '—')}</dd>
                        <dt>Transport Request</dt><dd>${escHtml(ci.transport_request || '—')}</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Description</h3>
                    <p>${escHtml(ci.description || 'No description.')}</p>
                    ${ci.notes ? `<h4 class="backlog-section-note">Notes</h4><p>${escHtml(ci.notes)}</p>` : ''}
                </div>
            </div>

            ${allowedMoves.length ? `
            <div class="backlog-quick__move-panel backlog-config-move">
                <div class="backlog-quick__move-head">
                    <p class="backlog-quick__move-title">Quick Move</p>
                    <span class="backlog-quick__move-copy">Update config item status directly from this screen.</span>
                </div>
                <div class="backlog-config-move__grid">
                    <div class="backlog-quick__move-field">
                        <label for="configQuickMoveStatus">Status</label>
                        <select id="configQuickMoveStatus" onchange="BacklogView.updateQuickMoveHint('config')">
                            ${allowedMoves.map(k => `<option value="${k}">${STATUS_LABELS[k] || k}</option>`).join('')}
                        </select>
                    </div>
                    <button class="pg-btn pg-btn--primary pg-btn--sm backlog-quick__move-cta" onclick="BacklogView.applyConfigQuickMove()">Apply</button>
                </div>
                <div class="backlog-quick__move-hint" id="configQuickMoveHint">${escHtml(_statusHelpText(allowedMoves[0]))}</div>
            </div>` : ''}

            <div class="card backlog-detail-card">
                <h3>📘 Functional Specification</h3>
                ${fs ? `
                    <dl class="detail-list">
                        <dt>Title</dt><dd>${escHtml(fs.title)}</dd>
                        <dt>Status</dt><dd>${PGStatusRegistry.badge(fs.status)}</dd>
                        <dt>Version</dt><dd>${fs.version || '—'}</dd>
                    </dl>
                ` : '<p class="backlog-detail-empty">No functional specification linked.</p>'}
            </div>

            <div class="card backlog-detail-card">
                <h3>📙 Technical Specification</h3>
                ${ts ? `
                    <dl class="detail-list">
                        <dt>Title</dt><dd>${escHtml(ts.title)}</dd>
                        <dt>Status</dt><dd><span class="badge badge-${ts.status}">${ts.status}</span></dd>
                    </dl>
                ` : '<p class="backlog-detail-empty">No technical specification linked.</p>'}
            </div>
        `;
    }

    // ── Detail View ──────────────────────────────────────────────────────
    async function openDetail(id) {
        try {
            currentItem = await API.get(`/backlog/${id}?include_specs=true`);
            await _ensureTeamMembers();
        } catch (err) { App.toast(err.message, 'error'); return; }
        currentDetailMode = 'view';
        currentDetailTab = 'overview';
        renderDetail('overview');
    }

    function renderDetail(activeTab = 'overview') {
        currentDetailTab = activeTab;
        const i = currentItem;
        const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
        const sprint = sprints.find(s => s.id === i.sprint_id);
        const main = document.getElementById('mainContent');
        const detailChangeNotice = currentDetailMode === 'view' && recentDetailChangeLabels.length
            ? `
                <div class="backlog-detail-change-notice">
                    <span class="backlog-detail-change-notice__label">Updated</span>
                    <div class="backlog-detail-change-notice__chips">
                        ${recentDetailChangeLabels.slice(0, 5).map((label) => `<span class="backlog-detail-change-notice__chip">${escHtml(label)}</span>`).join('')}
                        ${recentDetailChangeLabels.length > 5 ? `<span class="backlog-detail-change-notice__chip">+${recentDetailChangeLabels.length - 5} more</span>` : ''}
                    </div>
                </div>`
            : '';

        const fs = i.functional_spec;
        const ts = i.technical_spec || (fs ? fs.technical_spec : null);

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{label:'Backlog',onclick:'BacklogView.render()'},{label:escHtml(i.code||i.title)}])}
                <div class="backlog-detail-header">
                    <div class="backlog-detail-header__title-row">
                        <span class="wricef-badge" style="background:${w.color}">${w.label}</span>
                        <h2 class="pg-view-title">${escHtml(i.code || '')} ${escHtml(i.title)}</h2>
                        ${PGStatusRegistry.badge(i.status, { label: STATUS_LABELS[i.status] || i.status })}
                    </div>
                    <div class="backlog-detail-header__actions">
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.render()">← Back</button>
                        <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="BacklogView.showAIWricefSpecModal(${i.id})">AI WRICEF Spec</button>
                        ${currentDetailMode === 'edit'
                            ? `<button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.cancelInlineEdit()">Cancel Edit</button>`
                            : `<button class="pg-btn pg-btn--primary pg-btn--sm" onclick="BacklogView.showEditModal()">Edit</button>`}
                    </div>
                </div>
            </div>

            ${detailChangeNotice}

            ${currentDetailMode === 'edit' ? '' : `
            <div class="detail-tabs">
                <button class="detail-tab ${currentDetailTab === 'overview' ? 'active' : ''}" data-dtab="overview" onclick="BacklogView.switchDetailTab('overview')">📋 Overview</button>
                <button class="detail-tab ${currentDetailTab === 'specs' ? 'active' : ''}" data-dtab="specs" onclick="BacklogView.switchDetailTab('specs')">📑 Specs (FS/TS)</button>
                <button class="detail-tab ${currentDetailTab === 'tests' ? 'active' : ''}" data-dtab="tests" onclick="BacklogView.switchDetailTab('tests')">🧪 Tests</button>
                <button class="detail-tab ${currentDetailTab === 'trace' ? 'active' : ''}" data-dtab="trace" onclick="BacklogView.switchDetailTab('trace')">🔗 Traceability</button>
            </div>`}

            <div id="detailTabContent"></div>
        `;

        if (currentDetailMode === 'edit') {
            _renderDetailEditor(i);
            return;
        }

        _renderActiveDetailTab(currentDetailTab, i, w, sprint);
        recentDetailChangeFields = [];
        recentDetailChangeLabels = [];
    }

    function _renderActiveDetailTab(tab, item, wricefMeta, sprint) {
        if (tab === 'overview') _renderDetailOverview(item, wricefMeta, sprint);
        else if (tab === 'specs') _renderDetailSpecs(item);
        else if (tab === 'tests') _renderDetailTests(item);
        else if (tab === 'trace') _renderDetailTrace(item);
    }

    function switchDetailTab(tab) {
        currentDetailTab = tab;
        document.querySelectorAll('.detail-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.dtab === tab);
        });
        const i = currentItem;
        const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
        const sprint = sprints.find(s => s.id === i.sprint_id);
        _renderActiveDetailTab(tab, i, w, sprint);
    }

    function _detailHasRecentChange(fields) {
        return recentDetailChangeFields.some((field) => fields.includes(field));
    }

    function _detailRecentUpdateChip() {
        return '<span class="backlog-recent-update-chip">Updated</span>';
    }

    function _renderDetailOverview(i, w, sprint) {
        const fs = i.functional_spec;
        const ts = i.technical_spec || (fs ? fs.technical_spec : null);
        const specCoverage = fs && ts ? 'FS + TS Ready' : fs ? 'FS Ready' : 'Specs Pending';
        const specCoverageTone = fs && ts ? 'success' : fs ? 'info' : 'warning';
        const heroUpdated = _detailHasRecentChange(['title', 'wricef_type', 'code', 'description']);
        const moduleUpdated = _detailHasRecentChange(['module']);
        const ownerUpdated = _detailHasRecentChange(['assigned_to_id']);
        const sprintUpdated = _detailHasRecentChange(['sprint_id']);
        const planningUpdated = _detailHasRecentChange(['assigned_to_id', 'sprint_id', 'story_points', 'estimated_hours']);
        const designUpdated = _detailHasRecentChange(['wricef_type', 'sub_type', 'complexity', 'priority']);
        const sapUpdated = _detailHasRecentChange(['transaction_code', 'package', 'code']);
        const notesUpdated = _detailHasRecentChange(['description', 'acceptance_criteria', 'technical_notes', 'notes']);
        const allowedMoves = TRANSITIONS[i.status] || [];
        const currentFlowIndex = STATUS_FLOW_ORDER.indexOf(i.status);
        const statusFlow = STATUS_FLOW_ORDER.map((status, index) => {
            const isCurrent = status === i.status;
            const isReachable = allowedMoves.includes(status);
            const isComplete = currentFlowIndex > -1 && index < currentFlowIndex;
            const classNames = [
                'backlog-overview-status-flow__step',
                isCurrent ? 'is-current' : '',
                isReachable ? 'is-reachable' : '',
                isComplete ? 'is-complete' : '',
            ].filter(Boolean).join(' ');
            const disabledAttr = isCurrent || !isReachable ? 'disabled' : '';
            const progressLabel = isCurrent ? 'Current' : isReachable ? 'Next' : isComplete ? 'Completed' : 'Locked';
            return `
                <button type="button" class="${classNames}" ${disabledAttr} onclick="BacklogView.applyOverviewStatus('${status}')">
                    <span class="backlog-overview-status-flow__step-label">${STATUS_LABELS[status] || status}</span>
                    <span class="backlog-overview-status-flow__step-state">${progressLabel}</span>
                </button>
            `;
        }).join('');
        const exceptionActions = STATUS_EXCEPTION_ORDER
            .filter((status) => allowedMoves.includes(status))
            .map((status) => `
                <button type="button" class="backlog-overview-exception__action" onclick="BacklogView.applyOverviewStatus('${status}')">
                    ${STATUS_LABELS[status] || status}
                </button>
            `)
            .join('');

        document.getElementById('detailTabContent').innerHTML = `
            <div class="backlog-detail-content">
                <section class="backlog-overview-hero ${heroUpdated ? 'is-recently-updated' : ''}">
                    <div class="backlog-overview-hero__intro">
                        <p class="backlog-overview-hero__eyebrow">WRICEF Overview</p>
                        <h3>${escHtml(i.title || i.code || 'Backlog Item')}</h3>
                        <p class="backlog-overview-hero__copy">Keep delivery metadata, SAP object scope, and document readiness aligned before moving into detailed spec work.</p>
                    </div>
                    <div class="backlog-overview-hero__badges">
                        ${heroUpdated ? _detailRecentUpdateChip() : ''}
                        <span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label}</span>
                        ${PGStatusRegistry.badge(i.priority, { label: (i.priority || 'medium').toUpperCase() })}
                        ${PGStatusRegistry.badge(specCoverageTone, { label: specCoverage })}
                    </div>
                </section>

                <section class="backlog-overview-metrics">
                    <article class="backlog-overview-metric ${moduleUpdated ? 'is-recently-updated' : ''}">
                        <span class="backlog-overview-metric__label">Module</span>
                        <strong class="backlog-overview-metric__value">${escHtml(i.module || '—')}</strong>
                        <span class="backlog-overview-metric__hint">Functional area</span>
                    </article>
                    <article class="backlog-overview-metric ${ownerUpdated ? 'is-recently-updated' : ''}">
                        <span class="backlog-overview-metric__label">Owner</span>
                        <strong class="backlog-overview-metric__value">${escHtml(i.assigned_to || 'Unassigned')}</strong>
                        <span class="backlog-overview-metric__hint">Current delivery owner</span>
                    </article>
                    <article class="backlog-overview-metric ${sprintUpdated ? 'is-recently-updated' : ''}">
                        <span class="backlog-overview-metric__label">Sprint</span>
                        <strong class="backlog-overview-metric__value">${sprint ? escHtml(sprint.name) : 'Unassigned'}</strong>
                        <span class="backlog-overview-metric__hint">Planned execution window</span>
                    </article>
                    <article class="backlog-overview-metric">
                        <span class="backlog-overview-metric__label">Spec Coverage</span>
                        <strong class="backlog-overview-metric__value">${escHtml(specCoverage)}</strong>
                        <span class="backlog-overview-metric__hint">Documentation readiness</span>
                    </article>
                </section>

                <section class="backlog-overview-actions">
                    <article class="backlog-overview-action-card backlog-overview-action-card--status">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Delivery Control</p>
                                <h3>Status Progression</h3>
                            </div>
                            ${PGStatusRegistry.badge(i.status, { label: STATUS_LABELS[i.status] || i.status })}
                        </div>
                        <p class="backlog-overview-action-card__copy">${escHtml(_statusHelpText(i.status))}</p>
                        <div class="backlog-overview-status-flow">${statusFlow}</div>
                        ${exceptionActions ? `
                            <div class="backlog-overview-exception">
                                <span class="backlog-overview-exception__label">Alternate actions</span>
                                <div class="backlog-overview-exception__actions">${exceptionActions}</div>
                            </div>
                        ` : ''}
                    </article>

                    <article class="backlog-overview-action-card backlog-overview-action-card--planning ${planningUpdated ? 'is-recently-updated' : ''}">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Planning Workspace</p>
                                <h3>Sprint & Delivery Owner</h3>
                            </div>
                            ${planningUpdated ? _detailRecentUpdateChip() : '<span class="backlog-overview-planning__chip">Inline update</span>'}
                        </div>
                        <div class="backlog-overview-planning__grid">
                            <div class="backlog-overview-control">
                                <label for="overviewPlanningSprint">Sprint</label>
                                <input type="hidden" id="overviewPlanningSprint" value="${i.sprint_id ?? ''}">
                                <div id="overviewPlanningSprintDropdown" class="backlog-overview-control__dropdown"></div>
                                <span class="backlog-overview-control__hint">Execution window for the item.</span>
                            </div>
                            <div class="backlog-overview-control">
                                <label for="overviewPlanningOwner">Delivery Owner</label>
                                <input
                                    type="hidden"
                                    id="overviewPlanningOwner"
                                    value="${i.assigned_to_id ?? ''}"
                                    data-selected-label="${escHtml(i.assigned_to || '')}"
                                >
                                <div id="overviewPlanningOwnerDropdown" class="backlog-overview-control__dropdown"></div>
                                <span class="backlog-overview-control__hint">Primary accountable person for delivery follow-up.</span>
                            </div>
                        </div>
                        <div class="backlog-overview-planning__footer">
                            <span class="backlog-overview-planning__status" id="overviewPlanningHint">No planning changes pending.</span>
                            <button
                                type="button"
                                class="pg-btn pg-btn--primary pg-btn--sm"
                                id="overviewPlanningSave"
                                data-sprint-id="${i.sprint_id ?? ''}"
                                data-owner-id="${i.assigned_to_id ?? ''}"
                                onclick="BacklogView.applyOverviewPlanning()"
                                disabled
                            >Apply Planning</button>
                        </div>
                    </article>
                </section>

                <section class="backlog-overview-grid">
                    <article class="backlog-overview-card ${designUpdated ? 'is-recently-updated' : ''}">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Design Context</p>
                                <h3>Classification</h3>
                            </div>
                            ${designUpdated ? _detailRecentUpdateChip() : ''}
                        </div>
                        <dl class="backlog-overview-list">
                            <div class="backlog-overview-list__row"><dt>WRICEF Type</dt><dd><span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label}</span></dd></div>
                            <div class="backlog-overview-list__row"><dt>Sub Type</dt><dd>${escHtml(i.sub_type || '—')}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Complexity</dt><dd>${escHtml(i.complexity || 'medium')}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Priority</dt><dd>${PGStatusRegistry.badge(i.priority)}</dd></div>
                        </dl>
                    </article>

                    <article class="backlog-overview-card ${planningUpdated ? 'is-recently-updated' : ''}">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Delivery Planning</p>
                                <h3>Execution Snapshot</h3>
                            </div>
                            ${planningUpdated ? _detailRecentUpdateChip() : ''}
                        </div>
                        <dl class="backlog-overview-list">
                            <div class="backlog-overview-list__row"><dt>Story Points</dt><dd>${i.story_points || '—'}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Estimated Hours</dt><dd>${i.estimated_hours || '—'}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Actual Hours</dt><dd>${i.actual_hours || '—'}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Status</dt><dd>${PGStatusRegistry.badge(i.status, { label: STATUS_LABELS[i.status] || i.status })}</dd></div>
                        </dl>
                    </article>

                    <article class="backlog-overview-card ${sapUpdated ? 'is-recently-updated' : ''}">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">SAP Object Scope</p>
                                <h3>SAP Details</h3>
                            </div>
                            ${sapUpdated ? _detailRecentUpdateChip() : ''}
                        </div>
                        <dl class="backlog-overview-list">
                            <div class="backlog-overview-list__row"><dt>Transaction Code</dt><dd>${escHtml(i.transaction_code || '—')}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Package</dt><dd>${escHtml(i.package || '—')}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Transport Request</dt><dd>${escHtml(i.transport_request || '—')}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Code</dt><dd>${escHtml(i.code || '—')}</dd></div>
                        </dl>
                    </article>

                    <article class="backlog-overview-card">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Document Readiness</p>
                                <h3>Spec Status</h3>
                            </div>
                        </div>
                        <dl class="backlog-overview-list">
                            <div class="backlog-overview-list__row"><dt>Functional Spec</dt><dd>${fs ? PGStatusRegistry.badge(fs.status, { label: `FS • ${fs.status}` }) : '<span class="backlog-detail-muted">Not created</span>'}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Technical Spec</dt><dd>${ts ? PGStatusRegistry.badge(ts.status, { label: `TS • ${ts.status}` }) : '<span class="backlog-detail-muted">Not created</span>'}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Current Version</dt><dd>${escHtml(ts?.version || fs?.version || '—')}</dd></div>
                            <div class="backlog-overview-list__row"><dt>Reviewer</dt><dd>${escHtml(ts?.reviewer || fs?.reviewer || '—')}</dd></div>
                        </dl>
                    </article>
                </section>

                <section class="backlog-overview-rich-grid">
                    <article class="card backlog-detail-card backlog-detail-card--lead backlog-overview-rich-card ${notesUpdated ? 'is-recently-updated' : ''}">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Functional Summary</p>
                                <h3>Description</h3>
                            </div>
                            ${notesUpdated ? _detailRecentUpdateChip() : ''}
                        </div>
                        <p class="backlog-overview-copy">${escHtml(i.description || 'No description.')}</p>
                    </article>

                    ${i.acceptance_criteria ? `
                    <article class="card backlog-detail-card backlog-overview-rich-card">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Business Validation</p>
                                <h3>Acceptance Criteria</h3>
                            </div>
                        </div>
                        <p class="backlog-overview-copy">${escHtml(i.acceptance_criteria)}</p>
                    </article>` : ''}

                    ${i.technical_notes ? `
                    <article class="card backlog-detail-card backlog-overview-rich-card ${i.acceptance_criteria ? '' : 'backlog-overview-rich-card--wide'}">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Build Notes</p>
                                <h3>Technical Notes</h3>
                            </div>
                        </div>
                        <p class="backlog-overview-copy">${escHtml(i.technical_notes)}</p>
                    </article>` : ''}

                    ${i.notes ? `
                    <article class="card backlog-detail-card backlog-overview-rich-card ${!i.acceptance_criteria && !i.technical_notes ? 'backlog-overview-rich-card--wide' : ''}">
                        <div class="backlog-overview-card__head">
                            <div>
                                <p class="backlog-overview-card__eyebrow">Additional Context</p>
                                <h3>Notes</h3>
                            </div>
                        </div>
                        <p class="backlog-overview-copy">${escHtml(i.notes)}</p>
                    </article>` : ''}
                </section>
            </div>
        `;

        _initOverviewPlanningControls(i);
    }

    function _renderDetailSpecs(i) {
        const fs = i.functional_spec;
        const ts = fs ? fs.technical_spec : null;
        const needsGeneration = !fs || !ts;
        const readinessLabel = fs && ts ? 'FS + TS Ready' : fs ? 'FS Ready' : 'Specs Pending';
        const readinessTone = fs && ts ? 'success' : fs ? 'info' : 'warning';

        const renderSpecSummaryCard = (spec, specType, options = {}) => {
            const isFunctional = specType === 'fs';
            const icon = isFunctional ? '📘' : '📙';
            const label = isFunctional ? 'Functional Specification' : 'Technical Specification';
            const previewLabel = isFunctional ? 'Functional Document Preview' : 'Technical Document Preview';
            const previewTitle = isFunctional ? 'FS Content' : 'TS Content';
            const statusBadge = spec ? PGStatusRegistry.badge(spec.status, { label: `${isFunctional ? 'FS' : 'TS'} • ${spec.status}` }) : '';
            const reviewerRow = isFunctional ? `
                                <div class="backlog-spec-summary__meta-item">
                                    <span>Reviewer</span>
                                    <strong>${escHtml(spec.reviewer || '—')}</strong>
                                </div>` : '';

            if (!spec) {
                return `
                    <article class="card backlog-detail-card backlog-spec-summary-card backlog-spec-summary-card--empty">
                        <div class="backlog-spec-summary__hero">
                            <div class="backlog-spec-summary__hero-copy">
                                <p class="backlog-spec-summary__eyebrow">${isFunctional ? 'Functional Design' : 'Technical Build Design'}</p>
                                <h3>${icon} ${label}</h3>
                                <p class="backlog-spec-summary__text">${options.emptyText || 'Specification not available yet.'}</p>
                            </div>
                            ${isFunctional && needsGeneration ? `<button class="pg-btn pg-btn--primary pg-btn--sm" onclick="BacklogView._generateSpecs(${i.id})">✨ Generate Draft</button>` : ''}
                        </div>
                    </article>
                `;
            }

            return `
                <article class="card backlog-detail-card backlog-spec-summary-card">
                    <div class="backlog-spec-summary__hero">
                        <div class="backlog-spec-summary__hero-copy">
                            <p class="backlog-spec-summary__eyebrow">${isFunctional ? 'Functional Design' : 'Technical Build Design'}</p>
                            <h3>${icon} ${label}</h3>
                            <p class="backlog-spec-summary__title">${escHtml(spec.title)}</p>
                        </div>
                        <div class="backlog-spec-summary__hero-badges">
                            ${statusBadge}
                            ${spec.template_version ? `<span class="badge backlog-spec-template__badge">📋 Template v${escHtml(spec.template_version)}</span>` : ''}
                        </div>
                    </div>
                    <div class="backlog-spec-summary__meta-grid">
                        <div class="backlog-spec-summary__meta-item">
                            <span>Version</span>
                            <strong>${spec.version || '—'}</strong>
                        </div>
                        <div class="backlog-spec-summary__meta-item">
                            <span>Author</span>
                            <strong>${escHtml(spec.author || '—')}</strong>
                        </div>
                        ${reviewerRow}
                        <div class="backlog-spec-summary__meta-item">
                            <span>Approved By</span>
                            <strong>${escHtml(spec.approved_by || '—')}</strong>
                        </div>
                    </div>
                    ${options.actions || ''}
                    ${spec.content ? `
                        <div class="backlog-spec-content">
                            <div class="backlog-spec-content__header">
                                <div>
                                    <p class="backlog-spec-content__eyebrow">${previewLabel}</p>
                                    <h4>${previewTitle}</h4>
                                </div>
                                <span class="backlog-spec-content__hint">Rendered from markdown</span>
                            </div>
                            <div class="backlog-spec-content__body backlog-spec-markdown">${PGMarkdown.render(spec.content)}</div>
                        </div>
                    ` : ''}
                </article>
            `;
        };

        const fsActions = fs ? `
            <div class="backlog-spec-actions">
                ${fs.status === 'draft' ? `<button class="btn btn-sm btn-primary" onclick="BacklogView.updateSpecStatus('fs', ${fs.id}, 'in_review')">📤 Submit for Review</button>` : ''}
                ${fs.status === 'in_review' ? `<button class="btn btn-sm btn-success" onclick="BacklogView.updateSpecStatus('fs', ${fs.id}, 'approved')">✅ Approve</button>
                    <button class="btn btn-sm btn-warning" onclick="BacklogView.updateSpecStatus('fs', ${fs.id}, 'rework')">🔄 Rework</button>` : ''}
                ${fs.status === 'rework' ? `<button class="btn btn-sm btn-primary" onclick="BacklogView.updateSpecStatus('fs', ${fs.id}, 'in_review')">📤 Resubmit</button>` : ''}
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.printSpec('fs', ${fs.id}, '${escHtml(fs.title)}')">🖨️ Print / PDF</button>
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.downloadSpec('fs', ${fs.id}, '${escHtml(fs.title)}')">📥 Download</button>
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.editSpec('fs', ${fs.id})">✏️ Edit</button>
            </div>
        ` : '';

        const tsActions = ts ? `
            <div class="backlog-spec-actions">
                ${ts.status === 'draft' ? `<button class="btn btn-sm btn-primary" onclick="BacklogView.updateSpecStatus('ts', ${ts.id}, 'in_review')">📤 Submit for Review</button>` : ''}
                ${ts.status === 'in_review' ? `<button class="btn btn-sm btn-success" onclick="BacklogView.updateSpecStatus('ts', ${ts.id}, 'approved')">✅ Approve</button>
                    <button class="btn btn-sm btn-warning" onclick="BacklogView.updateSpecStatus('ts', ${ts.id}, 'rework')">🔄 Rework</button>` : ''}
                ${ts.status === 'rework' ? `<button class="btn btn-sm btn-primary" onclick="BacklogView.updateSpecStatus('ts', ${ts.id}, 'in_review')">📤 Resubmit</button>` : ''}
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.printSpec('ts', ${ts.id}, '${escHtml(ts.title)}')">🖨️ Print / PDF</button>
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.downloadSpec('ts', ${ts.id}, '${escHtml(ts.title)}')">📥 Download</button>
                <button class="btn btn-sm btn-secondary" onclick="BacklogView.editSpec('ts', ${ts.id})">✏️ Edit</button>
            </div>
        ` : '';

        document.getElementById('detailTabContent').innerHTML = `
            <section class="backlog-specs-hero">
                <div class="backlog-specs-hero__intro">
                    <p class="backlog-overview-hero__eyebrow">Specification Workspace</p>
                    <h3>Functional and technical documentation</h3>
                    <p class="backlog-overview-hero__copy">Review document readiness, ownership, and approval state before opening the full editor workspace.</p>
                </div>
                <div class="backlog-specs-hero__metrics">
                    <article class="backlog-overview-metric">
                        <span class="backlog-overview-metric__label">Readiness</span>
                        <strong class="backlog-overview-metric__value">${escHtml(readinessLabel)}</strong>
                        <span class="backlog-overview-metric__hint">Current spec coverage</span>
                    </article>
                    <article class="backlog-overview-metric">
                        <span class="backlog-overview-metric__label">Functional Spec</span>
                        <strong class="backlog-overview-metric__value">${fs ? escHtml(fs.version || 'Draft') : 'Missing'}</strong>
                        <span class="backlog-overview-metric__hint">${fs ? `Status: ${fs.status}` : 'Needs generation'}</span>
                    </article>
                    <article class="backlog-overview-metric">
                        <span class="backlog-overview-metric__label">Technical Spec</span>
                        <strong class="backlog-overview-metric__value">${ts ? escHtml(ts.version || 'Draft') : 'Pending'}</strong>
                        <span class="backlog-overview-metric__hint">${ts ? `Status: ${ts.status}` : 'Created after FS approval or generation'}</span>
                    </article>
                </div>
                ${needsGeneration ? `
                <div class="backlog-spec-toolbar backlog-spec-toolbar--hero">
                    <button class="btn btn-primary" onclick="BacklogView._generateSpecs(${i.id})" id="btnGenerateSpecs">
                        ✨ Generate Draft from Template
                    </button>
                </div>` : ''}
            </section>

            <section class="backlog-specs-grid">
                ${renderSpecSummaryCard(fs, 'fs', {
                    actions: fsActions,
                    emptyText: 'No functional specification linked yet.',
                })}

                ${renderSpecSummaryCard(ts, 'ts', {
                    actions: tsActions,
                    emptyText: fs ? 'Technical spec will be auto-created when FS is approved.' : 'No technical specification linked yet.',
                })}
            </section>
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
        container.innerHTML = '<div class="backlog-detail-loading"><div class="spinner"></div></div>';
        try {
            const chain = await API.get(`/traceability/backlog_item/${i.id}`);
            const testCases = (chain.downstream || []).filter(d => d.type === 'test_case');
            const defects = (chain.downstream || []).filter(d => d.type === 'defect');

            container.innerHTML = `
                <div class="card backlog-detail-card">
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
                        </table>` : '<p class="backlog-detail-empty">No test cases linked.</p>'}
                </div>
                <div class="card backlog-detail-card">
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
                        </table>` : '<p class="backlog-detail-empty">No defects linked.</p>'}
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div class="card backlog-detail-card"><p>Could not load test data.</p></div>`;
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
        container.innerHTML = '<div class="backlog-detail-loading"><div class="spinner"></div></div>';
        try {
            const chain = await API.get(`/traceability/backlog_item/${i.id}`);
            const upstream = chain.upstream || [];
            const downstream = chain.downstream || [];

            container.innerHTML = `
                <div class="card backlog-detail-card">
                    <h3>⬆️ Upstream (${upstream.length})</h3>
                    ${upstream.length > 0 ? `
                        <table class="data-table">
                            <thead><tr><th>Type</th><th>Title</th></tr></thead>
                            <tbody>${upstream.map(u => `
                                <tr><td><span class="badge">${u.type}</span></td><td>${escHtml(u.title)}</td></tr>`).join('')}
                            </tbody>
                        </table>` : '<p class="backlog-detail-empty">No upstream links.</p>'}
                </div>
                <div class="card backlog-detail-card">
                    <h3>⬇️ Downstream (${downstream.length})</h3>
                    ${downstream.length > 0 ? `
                        <table class="data-table">
                            <thead><tr><th>Type</th><th>Title</th></tr></thead>
                            <tbody>${downstream.map(d => `
                                <tr><td><span class="badge">${d.type}</span></td><td>${escHtml(d.title)}</td></tr>`).join('')}
                            </tbody>
                        </table>` : '<p class="backlog-detail-empty">No downstream links.</p>'}
                </div>
                <div class="card backlog-detail-card">
                    <h3>📊 Links Summary</h3>
                    <dl class="detail-list">
                        ${Object.entries(chain.links_summary || {}).map(([k, v]) =>
                            `<dt>${k}</dt><dd>${v}</dd>`).join('')}
                    </dl>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div class="card backlog-detail-card"><p>Could not load traceability data.</p></div>`;
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
                <div class="detail-grid backlog-stats-grid">
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
                <div class="backlog-stats-copy">
                    <p><strong>WRICEF Total Items:</strong> ${stats.total_items || 0}</p>
                    <p><strong>Total Story Points:</strong> ${stats.total_story_points || 0}</p>
                    <p><strong>Estimated Hours:</strong> ${stats.total_estimated_hours || 0}</p>
                    <p><strong>Actual Hours:</strong> ${stats.total_actual_hours || 0}</p>
                </div>
                <div class="detail-grid backlog-stats-grid backlog-stats-grid--spaced">
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
                <div class="backlog-stats-copy">
                    <p><strong>Config Total Items:</strong> ${cfgStats.total}</p>
                </div>
                <div class="backlog-stats-actions">
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
            <p class="backlog-create-copy">Select what you want to create.</p>
            <div class="backlog-create-grid">
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
        currentDetailReturnTab = currentDetailTab || 'overview';
        currentDetailMode = 'edit';
        renderDetail(currentDetailReturnTab);
    }

    function cancelInlineEdit() {
        currentDetailMode = 'view';
        renderDetail(currentDetailReturnTab || currentDetailTab || 'overview');
    }

    function _renderItemFormMarkup(item, options = {}) {
        const isEdit = !!item;
        const isInline = options.isInline === true;
        const members = options.members || [];
        const wricefMeta = WRICEF[item?.wricef_type] || WRICEF.enhancement;
        const assignedHtml = TeamMemberPicker.renderSelect('biAssigned', members, item?.assigned_to_id || item?.assigned_to || '', {
            cssClass: isInline ? 'backlog-editor-select' : 'form-input',
        });
        const currentSprint = sprints.find((entry) => String(entry.id) === String(item?.sprint_id || ''));
        const moduleOptions = ['FI','CO','MM','SD','PP','PM','QM','HCM','PS','WM','EWM','BTP','Basis','ABAP','Other'];
        const priorityOptions = ['low','medium','high','critical'];
        const complexityOptions = ['low','medium','high','very_high'];
        const wricefFieldHtml = isInline
            ? `
                <input type="hidden" id="biType" value="${escHtml(item?.wricef_type || 'enhancement')}" data-selected-label="${escHtml(wricefMeta.label)}">
                <div id="biTypeDropdown" class="backlog-overview-control__dropdown backlog-editor-control__dropdown"></div>
            `
            : `
                <select id="biType" class="form-input">
                    ${Object.entries(WRICEF).map(([k, v]) =>
                        `<option value="${k}" ${item?.wricef_type === k ? 'selected' : ''}>${v.icon} ${v.label}</option>`
                    ).join('')}
                </select>`;
        const moduleFieldHtml = isInline
            ? `
                <input type="hidden" id="biModule" value="${escHtml(item?.module || '')}" data-selected-label="${escHtml(item?.module || '—')}">
                <div id="biModuleDropdown" class="backlog-overview-control__dropdown backlog-editor-control__dropdown"></div>
            `
            : `
                <select id="biModule" class="form-input">
                    <option value="">—</option>
                    ${moduleOptions.map(m => `<option value="${m}" ${item?.module === m ? 'selected' : ''}>${m}</option>`).join('')}
                </select>`;
        const priorityFieldHtml = isInline
            ? `
                <input type="hidden" id="biPriority" value="${escHtml(item?.priority || 'medium')}" data-selected-label="${escHtml(item?.priority || 'medium')}">
                <div id="biPriorityDropdown" class="backlog-overview-control__dropdown backlog-editor-control__dropdown"></div>
            `
            : `
                <select id="biPriority" class="form-input">
                    ${priorityOptions.map(p => `<option value="${p}" ${(item?.priority || 'medium') === p ? 'selected' : ''}>${p}</option>`).join('')}
                </select>`;
        const complexityFieldHtml = isInline
            ? `
                <input type="hidden" id="biComplexity" value="${escHtml(item?.complexity || 'medium')}" data-selected-label="${escHtml(item?.complexity || 'medium')}">
                <div id="biComplexityDropdown" class="backlog-overview-control__dropdown backlog-editor-control__dropdown"></div>
            `
            : `
                <select id="biComplexity" class="form-input">
                    ${complexityOptions.map(c => `<option value="${c}" ${(item?.complexity || 'medium') === c ? 'selected' : ''}>${c}</option>`).join('')}
                </select>`;
        const assignedFieldHtml = isInline
            ? `
                <input type="hidden" id="biAssigned" value="${item?.assigned_to_id ?? ''}" data-selected-label="${escHtml(item?.assigned_to || '')}">
                <div id="biAssignedDropdown" class="backlog-overview-control__dropdown backlog-editor-control__dropdown"></div>
            `
            : assignedHtml;
        const sprintFieldHtml = isInline
            ? `
                <input type="hidden" id="biSprint" value="${item?.sprint_id ?? ''}" data-selected-label="${escHtml(currentSprint?.name || 'Unassigned')}">
                <div id="biSprintDropdown" class="backlog-overview-control__dropdown backlog-editor-control__dropdown"></div>
            `
            : `
                <select id="biSprint" class="form-input">
                    <option value="">Unassigned</option>
                    ${sprints.map(s => `<option value="${s.id}" ${item?.sprint_id === s.id ? 'selected' : ''}>${escHtml(s.name)}</option>`).join('')}
                </select>`;

        const definitionFields = `
            <div class="form-row">
                <div class="form-group"><label>Title *</label><input id="biTitle" class="form-input" value="${escHtml(item?.title || '')}"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>WRICEF Type *</label>
                    ${wricefFieldHtml}
                </div>
                <div class="form-group"><label>Code</label><input id="biCode" class="form-input" placeholder="e.g. ENH-FI-001" value="${escHtml(item?.code || '')}"></div>
            </div>
            <div class="form-group"><label>Description</label><textarea id="biDesc" class="form-input" rows="4">${escHtml(item?.description || '')}</textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Module</label>
                    ${moduleFieldHtml}
                </div>
                <div class="form-group"><label>Sub Type</label><input id="biSubType" class="form-input" placeholder="e.g. BAdI, RFC, ALV" value="${escHtml(item?.sub_type || '')}"></div>
            </div>`;

        const planningFields = `
            <div class="form-row">
                <div class="form-group"><label>Priority</label>
                    ${priorityFieldHtml}
                </div>
                <div class="form-group"><label>Complexity</label>
                    ${complexityFieldHtml}
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Story Points</label><input id="biSP" type="number" class="form-input" value="${item?.story_points || ''}"></div>
                <div class="form-group"><label>Estimated Hours</label><input id="biEstH" type="number" step="0.5" class="form-input" value="${item?.estimated_hours || ''}"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Assigned To</label>${assignedFieldHtml}</div>
                <div class="form-group"><label>Sprint</label>
                    ${sprintFieldHtml}
                </div>
            </div>`;

        const sapFields = `
            <div class="form-row">
                <div class="form-group"><label>Transaction Code</label><input id="biTCode" class="form-input" value="${escHtml(item?.transaction_code || '')}"></div>
                <div class="form-group"><label>Package</label><input id="biPkg" class="form-input" value="${escHtml(item?.package || '')}"></div>
            </div>`;

        const notesFields = `
            <div class="form-group"><label>Acceptance Criteria</label><textarea id="biAC" class="form-input" rows="3">${escHtml(item?.acceptance_criteria || '')}</textarea></div>
            <div class="form-group"><label>Technical Notes</label><textarea id="biTechNotes" class="form-input" rows="3">${escHtml(item?.technical_notes || '')}</textarea></div>
            <div class="form-group"><label>Notes</label><textarea id="biNotes" class="form-input" rows="3">${escHtml(item?.notes || '')}</textarea></div>
        `;

        if (!isInline) {
            return `${definitionFields}${planningFields}${sapFields}${notesFields}
                <div class="backlog-modal-actions">
                    <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button class="btn btn-primary" onclick="BacklogView.saveItem(${isEdit ? item.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
                </div>`;
        }

        return `
            <section class="backlog-editor-workspace">
                <div class="backlog-editor-workspace__hero">
                    <div>
                        <p class="backlog-editor-workspace__eyebrow">Inline Edit Workspace</p>
                        <h3>Edit Backlog Item</h3>
                        <p class="backlog-editor-workspace__copy">Update delivery metadata, SAP object scope, and ownership directly on the item detail screen.</p>
                    </div>
                    <div class="backlog-editor-workspace__meta">
                        <span class="wricef-badge" style="background:${wricefMeta.color}">${wricefMeta.icon} ${wricefMeta.label}</span>
                        ${PGStatusRegistry.badge(item?.status, { label: STATUS_LABELS[item?.status] || item?.status || 'Draft' })}
                    </div>
                </div>
                <div class="backlog-editor-grid">
                    <article class="backlog-editor-card backlog-editor-card--wide">
                        <div class="backlog-editor-card__head">
                            <div class="backlog-editor-card__title-block">
                                <p class="backlog-editor-card__eyebrow">Core Details</p>
                                <h4>Definition</h4>
                            </div>
                        </div>
                        <div class="backlog-editor-card__body">${definitionFields}</div>
                    </article>
                    <article class="backlog-editor-card backlog-editor-card--compact">
                        <div class="backlog-editor-card__head">
                            <div class="backlog-editor-card__title-block">
                                <p class="backlog-editor-card__eyebrow">Planning</p>
                                <h4>Execution Setup</h4>
                            </div>
                        </div>
                        <div class="backlog-editor-card__body">${planningFields}</div>
                    </article>
                    <article class="backlog-editor-card backlog-editor-card--compact">
                        <div class="backlog-editor-card__head">
                            <div class="backlog-editor-card__title-block">
                                <p class="backlog-editor-card__eyebrow">SAP Scope</p>
                                <h4>System Mapping</h4>
                            </div>
                        </div>
                        <div class="backlog-editor-card__body">${sapFields}</div>
                    </article>
                    <article class="backlog-editor-card backlog-editor-card--wide">
                        <div class="backlog-editor-card__head">
                            <div class="backlog-editor-card__title-block">
                                <p class="backlog-editor-card__eyebrow">Delivery Notes</p>
                                <h4>Working Context</h4>
                            </div>
                        </div>
                        <div class="backlog-editor-card__body">${notesFields}</div>
                    </article>
                </div>
                <div class="backlog-editor-actions">
                    <button class="pg-btn pg-btn--ghost" type="button" onclick="BacklogView.cancelInlineEdit()">Cancel</button>
                    <button class="pg-btn pg-btn--primary" type="button" onclick="BacklogView.saveItem(${item.id})">Save Changes</button>
                </div>
            </section>
        `;
    }

    function _renderDetailEditor(item) {
        document.getElementById('detailTabContent').innerHTML = _renderItemFormMarkup(item, {
            isInline: true,
            members: teamMembers,
        });
        _initDetailEditorControls(item);
    }

    function _setInlineEditorFieldValue(fieldId, value, label = '') {
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.value = value == null ? '' : String(value);
        field.dataset.selectedLabel = label || '';
    }

    function _getInlineEditorFieldValue(fieldId) {
        return document.getElementById(fieldId)?.value?.trim() || '';
    }

    function _getInlineEditorFieldLabel(fieldId) {
        return document.getElementById(fieldId)?.dataset.selectedLabel || '';
    }

    function _initDetailEditorControls(item) {
        const typeContainer = document.getElementById('biTypeDropdown');
        const moduleContainer = document.getElementById('biModuleDropdown');
        const priorityContainer = document.getElementById('biPriorityDropdown');
        const complexityContainer = document.getElementById('biComplexityDropdown');
        const assignedContainer = document.getElementById('biAssignedDropdown');
        const sprintContainer = document.getElementById('biSprintDropdown');
        if (!assignedContainer || !sprintContainer || !typeContainer || !moduleContainer || !priorityContainer || !complexityContainer || typeof TMDropdownSelect === 'undefined') return;

        TMDropdownSelect.render(typeContainer, {
            options: Object.entries(WRICEF).map(([key, meta]) => ({
                value: key,
                text: `${meta.icon} ${meta.label}`,
                selected: String(item.wricef_type || 'enhancement') === key,
            })),
            multi: false,
            searchable: false,
            placeholder: 'Select WRICEF type',
            onChange: (values) => {
                const nextValue = values[0] || 'enhancement';
                const matched = WRICEF[nextValue] || WRICEF.enhancement;
                _setInlineEditorFieldValue('biType', nextValue, matched.label);
            },
        });

        TMDropdownSelect.render(moduleContainer, {
            options: [{ value: '', text: '—', selected: !item.module }].concat(
                ['FI','CO','MM','SD','PP','PM','QM','HCM','PS','WM','EWM','BTP','Basis','ABAP','Other'].map((value) => ({
                    value,
                    text: value,
                    selected: String(item.module || '') === value,
                })),
            ),
            multi: false,
            searchable: false,
            placeholder: 'Select module',
            onChange: (values) => {
                const nextValue = values[0] || '';
                _setInlineEditorFieldValue('biModule', nextValue, nextValue || '—');
            },
        });

        TMDropdownSelect.render(priorityContainer, {
            options: ['low','medium','high','critical'].map((value) => ({
                value,
                text: value,
                selected: String(item.priority || 'medium') === value,
            })),
            multi: false,
            searchable: false,
            placeholder: 'Select priority',
            onChange: (values) => {
                const nextValue = values[0] || 'medium';
                _setInlineEditorFieldValue('biPriority', nextValue, nextValue);
            },
        });

        TMDropdownSelect.render(complexityContainer, {
            options: ['low','medium','high','very_high'].map((value) => ({
                value,
                text: value,
                selected: String(item.complexity || 'medium') === value,
            })),
            multi: false,
            searchable: false,
            placeholder: 'Select complexity',
            onChange: (values) => {
                const nextValue = values[0] || 'medium';
                _setInlineEditorFieldValue('biComplexity', nextValue, nextValue);
            },
        });

        TMDropdownSelect.render(assignedContainer, {
            options: [
                { value: '', text: 'Unassigned', selected: !item.assigned_to_id },
                ...teamMembers
                    .filter((member) => member.is_active !== false)
                    .map((member) => ({
                        value: String(member.id),
                        text: `${member.name || member.email || member.id}${member.role ? ` (${member.role})` : ''}`,
                        selected: String(item.assigned_to_id || '') === String(member.id),
                    })),
            ],
            multi: false,
            searchable: true,
            placeholder: 'Select owner',
            onChange: (values) => {
                const nextValue = values[0] || '';
                const matchedMember = teamMembers.find((member) => String(member.id) === nextValue);
                _setInlineEditorFieldValue('biAssigned', nextValue, matchedMember?.name || '');
            },
        });

        TMDropdownSelect.render(sprintContainer, {
            options: [
                { value: '', text: 'Unassigned', selected: !item.sprint_id },
                ...sprints.map((entry) => ({
                    value: String(entry.id),
                    text: entry.name || `Sprint ${entry.id}`,
                    selected: String(item.sprint_id || '') === String(entry.id),
                })),
            ],
            multi: false,
            searchable: false,
            placeholder: 'Select sprint',
            onChange: (values) => {
                const nextValue = values[0] || '';
                const matchedSprint = sprints.find((entry) => String(entry.id) === nextValue);
                _setInlineEditorFieldValue('biSprint', nextValue, matchedSprint?.name || 'Unassigned');
            },
        });
    }

    function _normalizeChangedFieldValue(field, source) {
        const value = source?.[field];
        if (field === 'estimated_hours') return value == null || value === '' ? null : Number(value);
        if (field === 'story_points' || field === 'assigned_to_id' || field === 'sprint_id') return value == null || value === '' ? null : Number(value);
        return value == null ? '' : String(value).trim();
    }

    function _collectDetailChangeLabels(originalItem, payload) {
        const fieldLabels = {
            title: 'Title',
            wricef_type: 'WRICEF Type',
            code: 'Code',
            description: 'Description',
            module: 'Module',
            sub_type: 'Sub Type',
            priority: 'Priority',
            complexity: 'Complexity',
            story_points: 'Story Points',
            estimated_hours: 'Estimated Hours',
            assigned_to_id: 'Delivery Owner',
            sprint_id: 'Sprint',
            transaction_code: 'Transaction Code',
            package: 'Package',
            acceptance_criteria: 'Acceptance Criteria',
            technical_notes: 'Technical Notes',
            notes: 'Notes',
        };

        return Object.entries(fieldLabels)
            .filter(([field]) => _normalizeChangedFieldValue(field, originalItem) !== _normalizeChangedFieldValue(field, payload))
            .map(([, label]) => label);
    }

    async function _showItemForm(item) {
        const isEdit = !!item;
        const title = isEdit ? 'Edit Backlog Item' : 'New Backlog Item';
        const members = await TeamMemberPicker.fetchMembers(programId);

        App.openModal(`
            <h2>${title}</h2>
            <div class="backlog-modal-scroll">
                ${_renderItemFormMarkup(item, { members })}
            </div>
        `);
    }

    async function saveItem(itemId) {
        const previousItem = currentItem ? { ...currentItem } : null;
        const isInlineEditor = Boolean(document.getElementById('biTypeDropdown'));
        const payload = {
            title: document.getElementById('biTitle').value.trim(),
            wricef_type: isInlineEditor ? _getInlineEditorFieldValue('biType') : document.getElementById('biType').value,
            code: document.getElementById('biCode').value.trim(),
            description: document.getElementById('biDesc').value.trim(),
            module: isInlineEditor ? _getInlineEditorFieldValue('biModule') : document.getElementById('biModule').value,
            sub_type: document.getElementById('biSubType').value.trim(),
            priority: isInlineEditor ? _getInlineEditorFieldValue('biPriority') : document.getElementById('biPriority').value,
            complexity: isInlineEditor ? _getInlineEditorFieldValue('biComplexity') : document.getElementById('biComplexity').value,
            story_points: parseInt(document.getElementById('biSP').value) || null,
            estimated_hours: parseFloat(document.getElementById('biEstH').value) || null,
            assigned_to: document.getElementById('biAssignedDropdown')
                ? _getInlineEditorFieldLabel('biAssigned') || null
                : TeamMemberPicker.selectedMemberName('biAssigned') || null,
            assigned_to_id: document.getElementById('biAssignedDropdown')
                ? parseInt(_getInlineEditorFieldValue('biAssigned'), 10) || null
                : document.getElementById('biAssigned').value.trim() || null,
            sprint_id: document.getElementById('biSprintDropdown')
                ? parseInt(_getInlineEditorFieldValue('biSprint'), 10) || null
                : parseInt(document.getElementById('biSprint').value, 10) || null,
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
                if (currentItem?.id === itemId) {
                    await _refreshCollections({ rerender: false });
                    currentItem = await API.get(`/backlog/${itemId}?include_specs=true`);
                    await _ensureTeamMembers();
                    recentDetailChangeLabels = _collectDetailChangeLabels(previousItem || {}, payload);
                    currentDetailMode = 'view';
                    renderDetail(currentDetailReturnTab || currentDetailTab || 'overview');
                    return;
                }
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

    function _toastBacklogMoveResult(result) {
        const fx = result?._side_effects || {};
        if (fx.functional_spec_created) {
            App.toast('Moved to Design — Draft FS created automatically', 'success');
        } else if (fx.unit_tests_created) {
            App.toast('Moved to Test — Unit test cases generated', 'success');
        } else {
            App.toast('Item updated', 'success');
        }
    }

    async function _reloadCurrentBacklogDetail(tab = currentDetailTab || 'overview') {
        if (!currentItem?.id) return;
        currentItem = await API.get(`/backlog/${currentItem.id}?include_specs=true`);
        await _ensureTeamMembers();
        renderDetail(tab);
    }

    function _setOverviewPlanningFieldValue(fieldId, value, label = '') {
        const field = document.getElementById(fieldId);
        if (!field) return;
        field.value = value == null ? '' : String(value);
        if (label !== undefined) field.dataset.selectedLabel = label || '';
    }

    function _getOverviewPlanningFieldValue(fieldId) {
        return document.getElementById(fieldId)?.value || '';
    }

    function _getOverviewPlanningFieldLabel(fieldId) {
        return document.getElementById(fieldId)?.dataset.selectedLabel || '';
    }

    function _initOverviewPlanningControls(item) {
        const sprintContainer = document.getElementById('overviewPlanningSprintDropdown');
        const ownerContainer = document.getElementById('overviewPlanningOwnerDropdown');
        if (!sprintContainer || !ownerContainer || typeof TMDropdownSelect === 'undefined') {
            return;
        }
        const currentSprint = sprints.find((entry) => String(entry.id) === String(item.sprint_id || ''));

        TMDropdownSelect.render(sprintContainer, {
            options: [
                { value: '', text: 'Unassigned', selected: !item.sprint_id },
                ...sprints.map((entry) => ({
                    value: String(entry.id),
                    text: entry.name || `Sprint ${entry.id}`,
                    selected: String(item.sprint_id || '') === String(entry.id),
                })),
            ],
            multi: false,
            searchable: false,
            placeholder: 'Select sprint',
            onChange: (values) => {
                const nextValue = values[0] || '';
                const matchedSprint = sprints.find((entry) => String(entry.id) === nextValue);
                _setOverviewPlanningFieldValue('overviewPlanningSprint', nextValue, matchedSprint?.name || 'Unassigned');
                onOverviewPlanningChange();
            },
        });

        TMDropdownSelect.render(ownerContainer, {
            options: [
                { value: '', text: 'Unassigned', selected: !item.assigned_to_id },
                ...teamMembers
                    .filter((member) => member.is_active !== false)
                    .map((member) => ({
                        value: String(member.id),
                        text: `${member.name || member.email || member.id}${member.role ? ` (${member.role})` : ''}`,
                        selected: String(item.assigned_to_id || '') === String(member.id),
                    })),
            ],
            multi: false,
            searchable: true,
            placeholder: 'Select owner',
            onChange: (values) => {
                const nextValue = values[0] || '';
                const matchedMember = teamMembers.find((member) => String(member.id) === nextValue);
                _setOverviewPlanningFieldValue(
                    'overviewPlanningOwner',
                    nextValue,
                    matchedMember?.name || '',
                );
                onOverviewPlanningChange();
            },
        });

        _setOverviewPlanningFieldValue('overviewPlanningSprint', item.sprint_id ?? '', currentSprint?.name || 'Unassigned');
        _setOverviewPlanningFieldValue('overviewPlanningOwner', item.assigned_to_id ?? '', item.assigned_to || '');
        onOverviewPlanningChange();
    }

    function onOverviewPlanningChange() {
        const saveBtn = document.getElementById('overviewPlanningSave');
        if (!saveBtn) return;
        const sprintValue = _getOverviewPlanningFieldValue('overviewPlanningSprint');
        const ownerValue = _getOverviewPlanningFieldValue('overviewPlanningOwner');
        const hasChanged = sprintValue !== (saveBtn.dataset.sprintId || '') || ownerValue !== (saveBtn.dataset.ownerId || '');
        saveBtn.disabled = !hasChanged;
        const hint = document.getElementById('overviewPlanningHint');
        if (hint) {
            hint.textContent = hasChanged
                ? 'Planning changes are ready to apply.'
                : 'No planning changes pending.';
        }
    }

    async function applyOverviewPlanning() {
        if (!currentItem) return;
        const saveBtn = document.getElementById('overviewPlanningSave');
        if (!saveBtn) return;

        const sprintValue = _getOverviewPlanningFieldValue('overviewPlanningSprint');
        const ownerValue = _getOverviewPlanningFieldValue('overviewPlanningOwner');
        const shouldUpdateSprint = sprintValue !== (saveBtn.dataset.sprintId || '');
        const shouldUpdateOwner = ownerValue !== (saveBtn.dataset.ownerId || '');

        if (!shouldUpdateSprint && !shouldUpdateOwner) {
            App.toast('No planning changes to apply', 'info');
            return;
        }

        saveBtn.disabled = true;
        saveBtn.textContent = 'Applying...';

        try {
            if (shouldUpdateSprint) {
                await API.patch(`/backlog/${currentItem.id}/move`, {
                    sprint_id: parseInt(sprintValue, 10) || null,
                });
            }

            if (shouldUpdateOwner) {
                await API.put(`/backlog/${currentItem.id}`, {
                    assigned_to: _getOverviewPlanningFieldLabel('overviewPlanningOwner') || null,
                    assigned_to_id: parseInt(ownerValue, 10) || null,
                });
            }

            await _refreshCollections({ rerender: _hasBacklogShell() });
            await _reloadCurrentBacklogDetail('overview');
            App.toast('Planning details updated', 'success');
        } catch (err) {
            App.toast(err.message, 'error');
        } finally {
            const button = document.getElementById('overviewPlanningSave');
            if (button) button.textContent = 'Apply Planning';
            onOverviewPlanningChange();
        }
    }

    async function applyOverviewStatus(status) {
        if (!currentItem || !status || status === currentItem.status) return;
        try {
            const result = await API.patch(`/backlog/${currentItem.id}/move`, { status });
            await _refreshCollections({ rerender: _hasBacklogShell() });
            await _reloadCurrentBacklogDetail('overview');
            _toastBacklogMoveResult(result);
        } catch (err) {
            App.toast(err.message, 'error');
        }
    }

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
            <div class="backlog-modal-actions">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="BacklogView.doMove()">Move</button>
            </div>
        `);
    }

    async function doMove() {
        try {
            const itemId = currentItem.id;
            const hasShell = _hasBacklogShell();
            const result = await API.patch(`/backlog/${currentItem.id}/move`, {
                status: document.getElementById('moveStatus').value,
                sprint_id: parseInt(document.getElementById('moveSprint').value) || null,
            });
            await _refreshCollections({ rerender: hasShell });
            App.closeModal();
            _toastBacklogMoveResult(result);
            if (hasShell) {
                await openDetail(itemId);
            } else {
                currentItem = await API.get(`/backlog/${itemId}?include_specs=true`);
                renderDetail();
            }
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function applyConfigQuickMove() {
        if (!currentConfigItem) return;
        try {
            const itemId = currentConfigItem.id;
            const payload = { status: document.getElementById('configQuickMoveStatus').value };
            await API.put(`/config-items/${currentConfigItem.id}`, payload);
            await _refreshCollections({ rerender: _hasBacklogShell() });
            App.toast('Config item moved', 'success');
            await openConfigDetail(itemId);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function applyQuickMove() {
        if (!currentItem) return;
        try {
            const itemId = currentItem.id;
            const hasShell = _hasBacklogShell();
            const result = await API.patch(`/backlog/${currentItem.id}/move`, {
                status: document.getElementById('quickMoveStatus').value,
                sprint_id: parseInt(document.getElementById('quickMoveSprint').value, 10) || null,
            });
            await _refreshCollections({ rerender: hasShell });
            _toastBacklogMoveResult(result);
            PGPanel.close();
            if (hasShell) {
                await openDetail(itemId);
            } else {
                currentItem = await API.get(`/backlog/${itemId}?include_specs=true`);
                renderDetail();
            }
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function updateQuickMoveHint(kind = 'backlog') {
        const selectId = kind === 'config' ? 'configQuickMoveStatus' : 'quickMoveStatus';
        const hintId = kind === 'config' ? 'configQuickMoveHint' : 'quickMoveHint';
        const status = document.getElementById(selectId)?.value;
        const hintEl = document.getElementById(hintId);
        if (hintEl) hintEl.textContent = _statusHelpText(status);
    }

    async function deleteItem(id) {
        _openConfirmModal('Delete Backlog Item', 'Delete this backlog item?', `BacklogView.deleteItemConfirmed(${id})`);
    }

    async function deleteItemConfirmed(id) {
        try {
            await API.delete(`/backlog/${id}`);
            App.closeModal();
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
            <div class="backlog-modal-actions">
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
        _openConfirmModal('Delete Sprint', 'Delete this sprint? Items will be unassigned.', `BacklogView.deleteSprintConfirmed(${id})`);
    }

    async function deleteSprintConfirmed(id) {
        try {
            await API.delete(`/sprints/${id}`);
            App.closeModal();
            App.toast('Sprint deleted', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Helpers ──────────────────────────────────────────────────────────
    function _openConfirmModal(title, message, confirmAction, opts = {}) {
        const testId = opts.testId || 'backlog-confirm-modal';
        const submitTestId = opts.submitTestId || 'backlog-confirm-submit';
        const cancelTestId = opts.cancelTestId || 'backlog-confirm-cancel';
        const confirmLabel = opts.confirmLabel || 'Delete';
        App.openModal(`
            <div class="modal" data-testid="${testId}">
                <div class="modal-header">
                    <h2>${escHtml(title)}</h2>
                    <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
                </div>
                <div class="modal-body">
                    <p class="pg-confirm-copy">${escHtml(message)}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-testid="${cancelTestId}" onclick="App.closeModal()">Cancel</button>
                    <button class="btn btn-danger" data-testid="${submitTestId}" onclick="${confirmAction}">${escHtml(confirmLabel)}</button>
                </div>
            </div>
        `);
    }

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

            await _refreshCollections({ rerender: _hasBacklogShell() });
            // Re-fetch item with specs and re-render detail
            await openDetail(currentItem.id);
            switchDetailTab('specs');
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function _buildSpecExportContext(specType, title) {
        const item = currentItem;
        const fs = item.functional_spec;
        const spec = specType === 'fs' ? fs : (fs ? fs.technical_spec : null);
        const exportLabel = specType === 'fs' ? 'Functional Specification' : 'Technical Specification';
        const exportTimestamp = new Date().toLocaleString('tr-TR', {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });

        return {
            item,
            spec,
            specType,
            title,
            exportLabel,
            metadata: [
                { label: 'Document Type', value: exportLabel },
                { label: 'Status', value: spec?.status || 'draft' },
                { label: 'Version', value: spec?.version || '—' },
                { label: 'Template Version', value: spec?.template_version || '—' },
                { label: 'WRICEF Item', value: item.code || item.title || '—' },
                { label: 'Module', value: item.module || '—' },
                { label: 'Exported At', value: exportTimestamp },
            ],
        };
    }

    function downloadSpec(specType, specId, title) {
        const exportContext = _buildSpecExportContext(specType, title);
        const { spec, exportLabel, metadata } = exportContext;
        if (!spec || !spec.content) {
            App.toast('No content to download', 'error');
            return;
        }

        const filename = `${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.html`;
        const html = PGMarkdown.buildDocumentHtml({
            title,
            subtitle: `${exportLabel} Export`,
            content: spec.content,
            metadata,
            variant: specType,
        });
        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    function printSpec(specType, specId, title) {
        const exportContext = _buildSpecExportContext(specType, title);
        const { spec, exportLabel, metadata } = exportContext;
        if (!spec || !spec.content) {
            App.toast('No content to print', 'error');
            return;
        }

        const html = PGMarkdown.buildDocumentHtml({
            title,
            subtitle: `${exportLabel} Print View`,
            content: spec.content,
            metadata,
            variant: specType,
            autoPrint: true,
        });
        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const popup = window.open(url, '_blank');
        if (!popup) {
            URL.revokeObjectURL(url);
            App.toast('Popup blocked. Allow popups to use Print / PDF.', 'warning');
            return;
        }
        popup.focus();
        window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    }

    function showAIWricefSpecModal(defaultItemId = null) {
        BacklogAI.openWricefSpecModal({ items, currentItem, defaultItemId });
    }

    async function runAIWricefSpec() {
        return BacklogAI.runWricefSpec();
    }

    function _slugifySpecSection(value, index) {
        const normalized = String(value || 'section')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
        return `${normalized || 'section'}-${index}`;
    }

    function _parseSpecContent(content) {
        const lines = String(content || '').replace(/\r\n/g, '\n').split('\n');
        const preamble = [];
        const sections = [];
        let currentSection = null;
        let hasEnteredNumberedSections = false;

        const commitSection = () => {
            if (!currentSection) return;
            sections.push({
                id: currentSection.id,
                title: currentSection.title,
                body: currentSection.bodyLines.join('\n').trim(),
            });
            currentSection = null;
        };

        lines.forEach((rawLine, index) => {
            const line = rawLine.trim();
            if (/^##\s+/.test(line)) {
                const isNumberedSection = /^##\s+\d+[.)]?\s+/.test(line);
                if (!hasEnteredNumberedSections && !isNumberedSection) {
                    preamble.push(rawLine);
                    return;
                }

                hasEnteredNumberedSections = true;
                commitSection();
                const title = line.replace(/^##\s+/, '').trim() || `Section ${sections.length + 1}`;
                currentSection = {
                    id: _slugifySpecSection(title, index),
                    title,
                    bodyLines: [],
                };
                return;
            }

            if (currentSection) currentSection.bodyLines.push(rawLine);
            else preamble.push(rawLine);
        });

        commitSection();

        if (!sections.length) {
            sections.push({
                id: 'main-content',
                title: 'Main Content',
                body: String(content || '').trim(),
            });
        }

        return {
            preamble: preamble.join('\n').trim(),
            sections,
        };
    }

    function _getSpecFromCurrentItem(specType) {
        const fs = currentItem?.functional_spec;
        return specType === 'fs' ? fs : (fs ? fs.technical_spec : null);
    }

    function _buildSpecEditorState(specType, specId) {
        const spec = _getSpecFromCurrentItem(specType);
        const parsed = _parseSpecContent(spec?.content || '');
        return {
            specType,
            specId,
            label: specType === 'fs' ? 'Functional Specification' : 'Technical Specification',
            title: spec?.title || '',
            author: spec?.author || '',
            reviewer: spec?.reviewer || '',
            status: spec?.status || 'draft',
            version: spec?.version || '—',
            templateVersion: spec?.template_version || '—',
            preamble: parsed.preamble,
            sections: parsed.sections,
            activePanel: 'meta',
            previewMode: 'rendered',
        };
    }

    function _getStructuredSpecSectionConfig(title) {
        const normalized = String(title || '').toLowerCase();
        if (normalized.includes('document control')) {
            return {
                type: 'document-control',
                description: 'Edit key document metadata as simple fields. The markdown control table will be rebuilt automatically.',
                fallbackRows: [
                    ['Document ID', ''],
                    ['Version', ''],
                    ['Status', ''],
                    ['Functional Owner', ''],
                    ['Reviewer', ''],
                    ['Planned Approval Date', ''],
                ],
            };
        }

        if (normalized.includes('traceability')) {
            return {
                type: 'traceability',
                description: 'Maintain upstream requirement links and SAP references without editing markdown tables manually.',
                fallbackRows: [
                    ['Requirement', ''],
                    ['Classification', ''],
                    ['Process Path', ''],
                    ['SAP Transaction / App', ''],
                    ['Related Notes', ''],
                ],
            };
        }

        if (normalized.includes('business context')) {
            return {
                type: 'business-context',
                description: 'Capture business purpose and scope boundaries in dedicated fields instead of editing bullet lists manually.',
            };
        }

        if (normalized.includes('solution overview') || normalized.includes('architecture')) {
            return {
                type: 'solution-overview',
                description: 'Capture the technical purpose and landscape components as structured fields while preserving markdown output.',
            };
        }

        if (normalized.includes('test scenarios') || normalized.includes('acceptance coverage')) {
            return {
                type: 'test-scenarios',
                description: 'Maintain representative scenarios and acceptance criteria as editable entries while the editor rebuilds markdown numbering.',
            };
        }

        if (normalized.includes('assumptions') || normalized.includes('dependencies')) {
            return {
                type: 'assumptions-dependencies',
                description: 'Maintain assumptions, dependencies, and upstream decisions as structured rows with owners and status values.',
            };
        }

        if (normalized.includes('open points') || normalized.includes('risks')) {
            return {
                type: 'open-points-risks',
                description: 'Track unresolved open points and delivery risks as structured cards instead of editing markdown tables manually.',
            };
        }

        return null;
    }

    function _parseListTextarea(value) {
        return String(value || '')
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean)
            .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').trim());
    }

    function _stringifyBulletList(items) {
        return (items || []).filter(Boolean).map((item) => `- ${item}`).join('\n');
    }

    function _parseBusinessContextSection(body) {
        const lines = String(body || '').replace(/\r\n/g, '\n').split('\n');
        const result = {
            purpose: '',
            inScope: [],
            outScope: [],
            extra: '',
        };
        let mode = 'purpose';
        const purposeLines = [];
        const extraLines = [];

        lines.forEach((rawLine) => {
            const line = rawLine.trim();
            if (/^\*\*Business Purpose:\*\*/i.test(line)) {
                mode = 'purpose';
                const inline = line.replace(/^\*\*Business Purpose:\*\*/i, '').trim();
                if (inline) purposeLines.push(inline);
                return;
            }
            if (/^\*\*In Scope:\*\*/i.test(line)) {
                mode = 'in-scope';
                return;
            }
            if (/^\*\*Out of Scope:\*\*/i.test(line)) {
                mode = 'out-scope';
                return;
            }
            if (!line) return;

            if (mode === 'purpose') {
                purposeLines.push(line);
                return;
            }
            if (mode === 'in-scope') {
                result.inScope.push(line.replace(/^[-*]\s+/, '').trim());
                return;
            }
            if (mode === 'out-scope') {
                if (/^[-*]\s+/.test(line)) {
                    result.outScope.push(line.replace(/^[-*]\s+/, '').trim());
                } else {
                    extraLines.push(rawLine);
                }
            }
        });

        result.purpose = purposeLines.join('\n').trim();
        result.extra = extraLines.join('\n').trim();
        return result;
    }

    function _stringifyBusinessContextSection(parsed) {
        const blocks = [
            `**Business Purpose:** ${parsed.purpose || ''}`.trimEnd(),
            '**In Scope:**',
            _stringifyBulletList(parsed.inScope || []),
            '**Out of Scope:**',
            _stringifyBulletList(parsed.outScope || []),
        ];

        if ((parsed.extra || '').trim()) blocks.push(parsed.extra.trim());
        return blocks.filter((block) => block !== '').join('\n\n').trim();
    }

    function _parseSolutionOverviewSection(body) {
        const lines = String(body || '').replace(/\r\n/g, '\n').split('\n');
        const result = {
            purpose: '',
            components: [],
            extra: '',
        };
        const purposeLines = [];
        const extraLines = [];
        let mode = 'purpose';

        lines.forEach((rawLine) => {
            const line = rawLine.trim();
            if (/^\*\*Technical Purpose:\*\*/i.test(line)) {
                mode = 'purpose';
                const inline = line.replace(/^\*\*Technical Purpose:\*\*/i, '').trim();
                if (inline) purposeLines.push(inline);
                return;
            }
            if (/^\*\*Landscape \/ Components:\*\*/i.test(line)) {
                mode = 'components';
                return;
            }
            if (!line) return;

            if (mode === 'purpose') {
                purposeLines.push(line);
                return;
            }

            if (mode === 'components') {
                result.components.push(line.replace(/^[-*]\s+/, '').trim());
                return;
            }

            extraLines.push(rawLine);
        });

        result.purpose = purposeLines.join('\n').trim();
        result.extra = extraLines.join('\n').trim();
        return result;
    }

    function _stringifySolutionOverviewSection(parsed) {
        const blocks = [
            '**Technical Purpose:**',
            (parsed.purpose || '').trim(),
            '**Landscape / Components:**',
            _stringifyBulletList(parsed.components || []),
        ];

        if ((parsed.extra || '').trim()) blocks.push(parsed.extra.trim());
        return blocks.filter((block) => block !== '').join('\n\n').trim();
    }

    function _parseTestScenariosSection(body) {
        const lines = String(body || '').replace(/\r\n/g, '\n').split('\n');
        const result = {
            intro: '',
            scenarios: [],
            acceptance: '',
            extra: '',
        };
        const introLines = [];
        const extraLines = [];
        let mode = 'intro';

        lines.forEach((rawLine) => {
            const line = rawLine.trim();
            if (!line) return;

            if (/^\*\*Acceptance Criteria:\*\*/i.test(line)) {
                mode = 'acceptance';
                result.acceptance = line.replace(/^\*\*Acceptance Criteria:\*\*/i, '').trim();
                return;
            }

            if (/^\d+\.\s+/.test(line)) {
                mode = 'scenarios';
                result.scenarios.push(line.replace(/^\d+\.\s+/, '').trim());
                return;
            }

            if (mode === 'intro') {
                introLines.push(line);
                return;
            }

            if (mode === 'acceptance') {
                result.acceptance = [result.acceptance, line].filter(Boolean).join('\n').trim();
                return;
            }

            extraLines.push(rawLine);
        });

        result.intro = introLines.join('\n').trim();
        result.extra = extraLines.join('\n').trim();
        return result;
    }

    function _stringifyTestScenariosSection(parsed) {
        const blocks = [];
        if ((parsed.intro || '').trim()) blocks.push(parsed.intro.trim());
        (parsed.scenarios || []).filter(Boolean).forEach((scenario, index) => {
            blocks.push(`${index + 1}. ${scenario}`);
        });
        blocks.push(`**Acceptance Criteria:** ${parsed.acceptance || ''}`.trimEnd());
        if ((parsed.extra || '').trim()) blocks.push(parsed.extra.trim());
        return blocks.filter((block) => block !== '').join('\n\n').trim();
    }

    function _parseAssumptionsDependenciesSection(body) {
        const parsed = _parseSectionTableBlock(body, [
            ['Assumption', '', '', 'Open'],
            ['Dependency', '', '', 'Open'],
            ['Upstream Decision', '', '', 'Open'],
        ]);

        const entries = (parsed.rows || []).map((row) => ({
            type: row[0] || 'Assumption',
            description: row[1] || '',
            owner: row[2] || '',
            status: row[3] || 'Open',
        }));

        return {
            before: parsed.before || '',
            after: parsed.after || '',
            entries: entries.length ? entries : [{ type: 'Assumption', description: '', owner: '', status: 'Open' }],
        };
    }

    function _stringifyAssumptionsDependenciesSection(parsed) {
        const rows = (parsed.entries || []).map((entry) => [
            entry.type || 'Assumption',
            entry.description || '',
            entry.owner || '',
            entry.status || 'Open',
        ]);

        return _buildStructuredSectionBody(
            {
                header: ['Type', 'Description', 'Owner', 'Status'],
                before: parsed.before || '',
            },
            rows.length ? rows : [['Assumption', '', '', 'Open']],
            parsed.after || ''
        );
    }

    function _parseOpenPointsRisksSection(body) {
        const parsed = _parseSectionTableBlock(body, [
            ['1', '', '', '', 'Open Point / Risk', 'Open'],
        ]);

        const entries = (parsed.rows || []).map((row, index) => ({
            number: row[0] || String(index + 1),
            description: row[1] || '',
            owner: row[2] || '',
            dueDate: row[3] || '',
            type: row[4] || 'Open Point / Risk',
            status: row[5] || 'Open',
        }));

        return {
            before: parsed.before || '',
            after: parsed.after || '',
            entries: entries.length ? entries : [{
                number: '1',
                description: '',
                owner: '',
                dueDate: '',
                type: 'Open Point / Risk',
                status: 'Open',
            }],
        };
    }

    function _stringifyOpenPointsRisksSection(parsed) {
        const rows = (parsed.entries || []).map((entry, index) => [
            entry.number || String(index + 1),
            entry.description || '',
            entry.owner || '',
            entry.dueDate || '',
            entry.type || 'Open Point / Risk',
            entry.status || 'Open',
        ]);

        return _buildStructuredSectionBody(
            {
                header: ['#', 'Description', 'Owner', 'Due Date', 'Type', 'Status'],
                before: parsed.before || '',
            },
            rows.length ? rows : [['1', '', '', '', 'Open Point / Risk', 'Open']],
            parsed.after || ''
        );
    }

    function _parseSectionTableBlock(body, fallbackRows = []) {
        const lines = String(body || '').replace(/\r\n/g, '\n').split('\n');
        let start = -1;
        let end = -1;

        for (let index = 0; index < lines.length - 1; index += 1) {
            if (lines[index].includes('|') && /^\|?\s*:?-{3,}/.test(lines[index + 1].trim())) {
                start = index;
                end = index + 2;
                while (end < lines.length && lines[end].includes('|') && lines[end].trim()) end += 1;
                break;
            }
        }

        const parseRow = (line) => line
            .trim()
            .replace(/^\|/, '')
            .replace(/\|$/, '')
            .split('|')
            .map((cell) => cell.trim());

        if (start === -1) {
            return {
                hasTable: false,
                header: ['Item', 'Value'],
                rows: fallbackRows.map((row) => [...row]),
                before: '',
                after: body.trim(),
            };
        }

        const header = parseRow(lines[start]);
        const rows = lines.slice(start + 2, end).map(parseRow);
        return {
            hasTable: true,
            header: header.length ? header : ['Item', 'Value'],
            rows: rows.length ? rows : fallbackRows.map((row) => [...row]),
            before: lines.slice(0, start).join('\n').trim(),
            after: lines.slice(end).join('\n').trim(),
        };
    }

    function _stringifySectionTableBlock(header, rows) {
        const safeHeader = (header && header.length ? header : ['Item', 'Value']).map((cell) => cell || '');
        const columnCount = safeHeader.length;
        const separator = `|${safeHeader.map(() => '---').join('|')}|`;
        const tableRows = rows.map((row) => {
            const padded = [...row];
            while (padded.length < columnCount) padded.push('');
            return `| ${padded.slice(0, columnCount).map((cell) => String(cell || '')).join(' | ')} |`;
        });

        return [
            `| ${safeHeader.join(' | ')} |`,
            separator,
            ...tableRows,
        ].join('\n');
    }

    function _buildStructuredSectionBody(parsed, rows, extraContent) {
        const blocks = [];
        if ((parsed.before || '').trim()) blocks.push(parsed.before.trim());
        blocks.push(_stringifySectionTableBlock(parsed.header, rows));
        if ((extraContent || '').trim()) blocks.push(extraContent.trim());
        return blocks.join('\n\n').trim();
    }

    function _buildGenericTableDefaultRow(header, rowCount) {
        const nextRow = (header || []).map(() => '');
        const firstHeader = String(header?.[0] || '').trim().toLowerCase();
        if (firstHeader === '#') nextRow[0] = String(rowCount + 1);
        else if (firstHeader.includes('test')) nextRow[0] = `UT-0${rowCount + 1}`;
        return nextRow;
    }

    function _renderGenericTableSectionForm(section, sectionIndex, parsed) {
        const gridColumns = `repeat(${Math.min(Math.max(parsed.header.length, 1), 3)}, minmax(0, 1fr))`;
        const rows = parsed.rows.length ? parsed.rows : [_buildGenericTableDefaultRow(parsed.header, 0)];

        return `
            <div class="backlog-spec-editor__stack">
                <div class="backlog-spec-editor__section-head">
                    <div>
                        <p class="backlog-spec-content__eyebrow">Section ${sectionIndex + 1}</p>
                        <h3>${escHtml(section.title)}</h3>
                    </div>
                    <div class="backlog-spec-editor__section-actions">
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addGenericTableRow(${sectionIndex})">+ Row</button>
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add Section</button>
                    </div>
                </div>
                <div class="form-group">
                    <label>Section Title</label>
                    <input class="form-input" value="${escHtml(section.title)}" oninput="BacklogView.updateSpecEditorSectionTitle(${sectionIndex}, this.value)">
                </div>
                <div class="backlog-spec-editor__structured-card">
                    <p class="backlog-spec-editor__hint">Detected markdown table. Edit the table as structured fields; markdown is rebuilt automatically.</p>
                    <div class="form-group">
                        <label>Intro Markdown Above Table</label>
                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateGenericTableBefore(${sectionIndex}, this.value)">${escHtml(parsed.before || '')}</textarea>
                    </div>
                    <div class="backlog-spec-editor__entry-list">
                        ${rows.map((row, rowIndex) => `
                            <div class="backlog-spec-editor__entry-card">
                                <div class="backlog-spec-editor__entry-head">
                                    <strong>Row ${rowIndex + 1}</strong>
                                    <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.removeGenericTableRow(${sectionIndex}, ${rowIndex})">Remove</button>
                                </div>
                                <div class="backlog-spec-editor__entry-grid" style="grid-template-columns: ${gridColumns};">
                                    ${parsed.header.map((column, columnIndex) => `
                                        <div class="form-group">
                                            <label>${escHtml(column || `Column ${columnIndex + 1}`)}</label>
                                            <input class="form-input" value="${escHtml(row[columnIndex] || '')}" oninput="BacklogView.updateGenericTableCell(${sectionIndex}, ${rowIndex}, ${columnIndex}, this.value)">
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="form-group">
                    <label>Additional Markdown Below Table</label>
                    <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateGenericTableAfter(${sectionIndex}, this.value)">${escHtml(parsed.after || '')}</textarea>
                </div>
            </div>
        `;
    }

    function _renderStructuredSectionForm(section, sectionIndex, config) {
        if (config.type === 'business-context') {
            const parsed = _parseBusinessContextSection(section.body);
            return `
                <div class="backlog-spec-editor__stack">
                    <div class="backlog-spec-editor__section-head">
                        <div>
                            <p class="backlog-spec-content__eyebrow">Section ${sectionIndex + 1}</p>
                            <h3>${escHtml(section.title)}</h3>
                        </div>
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add Section</button>
                    </div>
                    <div class="form-group">
                        <label>Section Title</label>
                        <input class="form-input" value="${escHtml(section.title)}" oninput="BacklogView.updateSpecEditorSectionTitle(${sectionIndex}, this.value)">
                    </div>
                    <div class="backlog-spec-editor__structured-card">
                        <p class="backlog-spec-editor__hint">${escHtml(config.description)}</p>
                        <div class="form-group">
                            <label>Business Purpose</label>
                            <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateBusinessContextField(${sectionIndex}, 'purpose', this.value)">${escHtml(parsed.purpose)}</textarea>
                        </div>
                        <div class="backlog-spec-editor__structured-grid">
                            <div class="form-group">
                                <label>In Scope Items</label>
                                <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateBusinessContextField(${sectionIndex}, 'inScope', this.value)">${escHtml((parsed.inScope || []).join('\n'))}</textarea>
                                <p class="backlog-spec-editor__hint">One item per line.</p>
                            </div>
                            <div class="form-group">
                                <label>Out of Scope Items</label>
                                <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateBusinessContextField(${sectionIndex}, 'outScope', this.value)">${escHtml((parsed.outScope || []).join('\n'))}</textarea>
                                <p class="backlog-spec-editor__hint">One item per line.</p>
                            </div>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Additional Markdown</label>
                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateBusinessContextField(${sectionIndex}, 'extra', this.value)">${escHtml(parsed.extra || '')}</textarea>
                    </div>
                </div>
            `;
        }

        if (config.type === 'solution-overview') {
            const parsed = _parseSolutionOverviewSection(section.body);
            return `
                <div class="backlog-spec-editor__stack">
                    <div class="backlog-spec-editor__section-head">
                        <div>
                            <p class="backlog-spec-content__eyebrow">Section ${sectionIndex + 1}</p>
                            <h3>${escHtml(section.title)}</h3>
                        </div>
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add Section</button>
                    </div>
                    <div class="form-group">
                        <label>Section Title</label>
                        <input class="form-input" value="${escHtml(section.title)}" oninput="BacklogView.updateSpecEditorSectionTitle(${sectionIndex}, this.value)">
                    </div>
                    <div class="backlog-spec-editor__structured-card">
                        <p class="backlog-spec-editor__hint">${escHtml(config.description)}</p>
                        <div class="form-group">
                            <label>Technical Purpose</label>
                            <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateSolutionOverviewField(${sectionIndex}, 'purpose', this.value)">${escHtml(parsed.purpose)}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Landscape / Components</label>
                            <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateSolutionOverviewField(${sectionIndex}, 'components', this.value)">${escHtml((parsed.components || []).join('\n'))}</textarea>
                            <p class="backlog-spec-editor__hint">One component or system line per row.</p>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Additional Markdown</label>
                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateSolutionOverviewField(${sectionIndex}, 'extra', this.value)">${escHtml(parsed.extra || '')}</textarea>
                    </div>
                </div>
            `;
        }

        if (config.type === 'test-scenarios') {
            const parsed = _parseTestScenariosSection(section.body);
            const scenarios = parsed.scenarios.length ? parsed.scenarios : [''];
            return `
                <div class="backlog-spec-editor__stack">
                    <div class="backlog-spec-editor__section-head">
                        <div>
                            <p class="backlog-spec-content__eyebrow">Section ${sectionIndex + 1}</p>
                            <h3>${escHtml(section.title)}</h3>
                        </div>
                        <div class="backlog-spec-editor__section-actions">
                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addTestScenarioEntry(${sectionIndex})">+ Scenario</button>
                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add Section</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Section Title</label>
                        <input class="form-input" value="${escHtml(section.title)}" oninput="BacklogView.updateSpecEditorSectionTitle(${sectionIndex}, this.value)">
                    </div>
                    <div class="backlog-spec-editor__structured-card">
                        <p class="backlog-spec-editor__hint">${escHtml(config.description)}</p>
                        <div class="form-group">
                            <label>Intro Copy</label>
                            <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateTestScenarioField(${sectionIndex}, 'intro', this.value)">${escHtml(parsed.intro)}</textarea>
                        </div>
                        <div class="backlog-spec-editor__scenario-list">
                            ${scenarios.map((scenario, scenarioIndex) => `
                                <div class="backlog-spec-editor__scenario-card">
                                    <div class="backlog-spec-editor__scenario-head">
                                        <strong>Scenario ${scenarioIndex + 1}</strong>
                                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.removeTestScenarioEntry(${sectionIndex}, ${scenarioIndex})">Remove</button>
                                    </div>
                                    <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateTestScenarioEntry(${sectionIndex}, ${scenarioIndex}, this.value)">${escHtml(scenario)}</textarea>
                                </div>
                            `).join('')}
                        </div>
                        <div class="form-group">
                            <label>Acceptance Criteria</label>
                            <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateTestScenarioField(${sectionIndex}, 'acceptance', this.value)">${escHtml(parsed.acceptance)}</textarea>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Additional Markdown</label>
                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateTestScenarioField(${sectionIndex}, 'extra', this.value)">${escHtml(parsed.extra || '')}</textarea>
                    </div>
                </div>
            `;
        }

        if (config.type === 'assumptions-dependencies') {
            const parsed = _parseAssumptionsDependenciesSection(section.body);
            return `
                <div class="backlog-spec-editor__stack">
                    <div class="backlog-spec-editor__section-head">
                        <div>
                            <p class="backlog-spec-content__eyebrow">Section ${sectionIndex + 1}</p>
                            <h3>${escHtml(section.title)}</h3>
                        </div>
                        <div class="backlog-spec-editor__section-actions">
                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addAssumptionDependencyEntry(${sectionIndex})">+ Row</button>
                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add Section</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Section Title</label>
                        <input class="form-input" value="${escHtml(section.title)}" oninput="BacklogView.updateSpecEditorSectionTitle(${sectionIndex}, this.value)">
                    </div>
                    <div class="backlog-spec-editor__structured-card">
                        <p class="backlog-spec-editor__hint">${escHtml(config.description)}</p>
                        <div class="backlog-spec-editor__entry-list">
                            ${parsed.entries.map((entry, entryIndex) => `
                                <div class="backlog-spec-editor__entry-card">
                                    <div class="backlog-spec-editor__entry-head">
                                        <strong>Entry ${entryIndex + 1}</strong>
                                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.removeAssumptionDependencyEntry(${sectionIndex}, ${entryIndex})">Remove</button>
                                    </div>
                                    <div class="backlog-spec-editor__entry-grid backlog-spec-editor__entry-grid--double">
                                        <div class="form-group">
                                            <label>Type</label>
                                            <input class="form-input" value="${escHtml(entry.type)}" oninput="BacklogView.updateAssumptionDependencyField(${sectionIndex}, ${entryIndex}, 'type', this.value)">
                                        </div>
                                        <div class="form-group">
                                            <label>Status</label>
                                            <input class="form-input" value="${escHtml(entry.status)}" oninput="BacklogView.updateAssumptionDependencyField(${sectionIndex}, ${entryIndex}, 'status', this.value)">
                                        </div>
                                    </div>
                                    <div class="form-group">
                                        <label>Description</label>
                                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--compact" oninput="BacklogView.updateAssumptionDependencyField(${sectionIndex}, ${entryIndex}, 'description', this.value)">${escHtml(entry.description)}</textarea>
                                    </div>
                                    <div class="form-group">
                                        <label>Owner</label>
                                        <input class="form-input" value="${escHtml(entry.owner)}" oninput="BacklogView.updateAssumptionDependencyField(${sectionIndex}, ${entryIndex}, 'owner', this.value)">
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Additional Markdown</label>
                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateAssumptionDependencyExtra(${sectionIndex}, this.value)">${escHtml(parsed.after || '')}</textarea>
                    </div>
                </div>
            `;
        }

        if (config.type === 'open-points-risks') {
            const parsed = _parseOpenPointsRisksSection(section.body);
            return `
                <div class="backlog-spec-editor__stack">
                    <div class="backlog-spec-editor__section-head">
                        <div>
                            <p class="backlog-spec-content__eyebrow">Section ${sectionIndex + 1}</p>
                            <h3>${escHtml(section.title)}</h3>
                        </div>
                        <div class="backlog-spec-editor__section-actions">
                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addOpenPointRiskEntry(${sectionIndex})">+ Item</button>
                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add Section</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Section Title</label>
                        <input class="form-input" value="${escHtml(section.title)}" oninput="BacklogView.updateSpecEditorSectionTitle(${sectionIndex}, this.value)">
                    </div>
                    <div class="backlog-spec-editor__structured-card">
                        <p class="backlog-spec-editor__hint">${escHtml(config.description)}</p>
                        <div class="backlog-spec-editor__entry-list">
                            ${parsed.entries.map((entry, entryIndex) => `
                                <div class="backlog-spec-editor__entry-card">
                                    <div class="backlog-spec-editor__entry-head">
                                        <strong>Open Item ${entry.number || entryIndex + 1}</strong>
                                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.removeOpenPointRiskEntry(${sectionIndex}, ${entryIndex})">Remove</button>
                                    </div>
                                    <div class="backlog-spec-editor__entry-grid backlog-spec-editor__entry-grid--triple">
                                        <div class="form-group">
                                            <label>Reference</label>
                                            <input class="form-input" value="${escHtml(entry.number)}" oninput="BacklogView.updateOpenPointRiskField(${sectionIndex}, ${entryIndex}, 'number', this.value)">
                                        </div>
                                        <div class="form-group">
                                            <label>Type</label>
                                            <input class="form-input" value="${escHtml(entry.type)}" oninput="BacklogView.updateOpenPointRiskField(${sectionIndex}, ${entryIndex}, 'type', this.value)">
                                        </div>
                                        <div class="form-group">
                                            <label>Status</label>
                                            <input class="form-input" value="${escHtml(entry.status)}" oninput="BacklogView.updateOpenPointRiskField(${sectionIndex}, ${entryIndex}, 'status', this.value)">
                                        </div>
                                    </div>
                                    <div class="form-group">
                                        <label>Description</label>
                                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--compact" oninput="BacklogView.updateOpenPointRiskField(${sectionIndex}, ${entryIndex}, 'description', this.value)">${escHtml(entry.description)}</textarea>
                                    </div>
                                    <div class="backlog-spec-editor__entry-grid backlog-spec-editor__entry-grid--double">
                                        <div class="form-group">
                                            <label>Owner</label>
                                            <input class="form-input" value="${escHtml(entry.owner)}" oninput="BacklogView.updateOpenPointRiskField(${sectionIndex}, ${entryIndex}, 'owner', this.value)">
                                        </div>
                                        <div class="form-group">
                                            <label>Due Date</label>
                                            <input class="form-input" value="${escHtml(entry.dueDate)}" oninput="BacklogView.updateOpenPointRiskField(${sectionIndex}, ${entryIndex}, 'dueDate', this.value)">
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Additional Markdown</label>
                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateOpenPointRiskExtra(${sectionIndex}, this.value)">${escHtml(parsed.after || '')}</textarea>
                    </div>
                </div>
            `;
        }

        const parsed = _parseSectionTableBlock(section.body, config.fallbackRows);
        const rowMarkup = parsed.rows.map((row, rowIndex) => `
            <div class="backlog-spec-editor__structured-row">
                <label>${escHtml(row[0] || `Field ${rowIndex + 1}`)}</label>
                <input class="form-input" value="${escHtml(row[1] || '')}" oninput="BacklogView.updateStructuredSpecRow(${sectionIndex}, ${rowIndex}, this.value)">
            </div>
        `).join('');

        return `
            <div class="backlog-spec-editor__stack">
                <div class="backlog-spec-editor__section-head">
                    <div>
                        <p class="backlog-spec-content__eyebrow">Section ${sectionIndex + 1}</p>
                        <h3>${escHtml(section.title)}</h3>
                    </div>
                    <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add Section</button>
                </div>
                <div class="form-group">
                    <label>Section Title</label>
                    <input class="form-input" value="${escHtml(section.title)}" oninput="BacklogView.updateSpecEditorSectionTitle(${sectionIndex}, this.value)">
                </div>
                <div class="backlog-spec-editor__structured-card">
                    <p class="backlog-spec-editor__hint">${escHtml(config.description)}</p>
                    <div class="backlog-spec-editor__structured-grid">
                        ${rowMarkup}
                    </div>
                </div>
                <div class="form-group">
                    <label>Additional Markdown Under This Table</label>
                    <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--notes" oninput="BacklogView.updateStructuredSpecExtra(${sectionIndex}, this.value)">${escHtml(parsed.after || '')}</textarea>
                </div>
            </div>
        `;
    }

    function _serializeSpecEditorContent() {
        if (!specEditorState) return '';

        const blocks = [];
        if ((specEditorState.preamble || '').trim()) {
            blocks.push(specEditorState.preamble.trim());
        }

        specEditorState.sections.forEach((section) => {
            const title = (section.title || '').trim() || 'Untitled Section';
            blocks.push(`## ${title}`);
            if ((section.body || '').trim()) blocks.push(section.body.trim());
        });

        return blocks.join('\n\n').trim();
    }

    function _renderSpecEditorNav() {
        const nav = document.getElementById('specEditorNav');
        if (!nav || !specEditorState) return;

        nav.innerHTML = `
            <button class="backlog-spec-editor__nav-item ${specEditorState.activePanel === 'meta' ? 'active' : ''}" onclick="BacklogView.selectSpecEditorPanel('meta')">
                <span class="backlog-spec-editor__nav-title">Metadata & Intro</span>
                <span class="backlog-spec-editor__nav-copy">Title, owners, document header</span>
            </button>
            ${specEditorState.sections.map((section, index) => `
                <button class="backlog-spec-editor__nav-item ${specEditorState.activePanel === section.id ? 'active' : ''}" onclick="BacklogView.selectSpecEditorPanel('${section.id}')">
                    <span class="backlog-spec-editor__nav-index">${index + 1}</span>
                    <span>
                        <span class="backlog-spec-editor__nav-title">${escHtml(section.title)}</span>
                        <span class="backlog-spec-editor__nav-copy">Section content</span>
                    </span>
                </button>
            `).join('')}
        `;
    }

    function _renderSpecEditorPanel() {
        const panel = document.getElementById('specEditorPanel');
        if (!panel || !specEditorState) return;

        if (specEditorState.activePanel === 'meta') {
            panel.innerHTML = `
                <div class="backlog-spec-editor__stack">
                    <div class="backlog-spec-editor__meta-grid">
                        <div class="form-group">
                            <label>Document Title</label>
                            <input class="form-input" value="${escHtml(specEditorState.title)}" oninput="BacklogView.updateSpecEditorField('title', this.value)">
                        </div>
                        <div class="form-group">
                            <label>Author</label>
                            <input class="form-input" value="${escHtml(specEditorState.author)}" oninput="BacklogView.updateSpecEditorField('author', this.value)">
                        </div>
                        <div class="form-group">
                            <label>Reviewer</label>
                            <input class="form-input" value="${escHtml(specEditorState.reviewer)}" oninput="BacklogView.updateSpecEditorField('reviewer', this.value)">
                        </div>
                        <div class="backlog-spec-editor__meta-card">
                            <div><span>Status</span><strong>${escHtml(specEditorState.status)}</strong></div>
                            <div><span>Version</span><strong>${escHtml(specEditorState.version)}</strong></div>
                            <div><span>Template</span><strong>${escHtml(specEditorState.templateVersion)}</strong></div>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Document Intro / Header</label>
                        <textarea class="form-input backlog-spec-editor__textarea backlog-spec-editor__textarea--intro" oninput="BacklogView.updateSpecEditorPreamble(this.value)">${escHtml(specEditorState.preamble)}</textarea>
                        <p class="backlog-spec-editor__hint">Use this area for the main heading, summary tables, and any content that appears before the numbered sections.</p>
                    </div>
                </div>
            `;
            return;
        }

        const sectionIndex = specEditorState.sections.findIndex((section) => section.id === specEditorState.activePanel);
        const section = specEditorState.sections[sectionIndex];
        if (!section) return;

        const structuredConfig = _getStructuredSpecSectionConfig(section.title);
        if (structuredConfig) {
            panel.innerHTML = _renderStructuredSectionForm(section, sectionIndex, structuredConfig);
            return;
        }

        const parsedTable = _parseSectionTableBlock(section.body, []);
        if (parsedTable.hasTable) {
            panel.innerHTML = _renderGenericTableSectionForm(section, sectionIndex, parsedTable);
            return;
        }

        panel.innerHTML = `
            <div class="backlog-spec-editor__stack">
                <div class="backlog-spec-editor__section-head">
                    <div>
                        <p class="backlog-spec-content__eyebrow">Section ${sectionIndex + 1}</p>
                        <h3>${escHtml(section.title)}</h3>
                    </div>
                    <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add Section</button>
                </div>
                <div class="form-group">
                    <label>Section Title</label>
                    <input class="form-input" value="${escHtml(section.title)}" oninput="BacklogView.updateSpecEditorSectionTitle(${sectionIndex}, this.value)">
                </div>
                <div class="form-group">
                    <label>Section Content</label>
                    <textarea class="form-input backlog-spec-editor__textarea" oninput="BacklogView.updateSpecEditorSectionBody(${sectionIndex}, this.value)">${escHtml(section.body)}</textarea>
                    <p class="backlog-spec-editor__hint">Markdown tables, bullets, and notes are preserved. Keep content section-focused; the live preview on the right updates instantly.</p>
                </div>
            </div>
        `;
    }

    function _renderSpecEditorPreview() {
        const preview = document.getElementById('specEditorPreview');
        const title = document.getElementById('specEditorWorkspaceTitle');
        if (!preview || !specEditorState) return;

        const content = _serializeSpecEditorContent();
        if (title) title.textContent = specEditorState.title || specEditorState.label;

        if (specEditorState.previewMode === 'markdown') {
            preview.innerHTML = `<pre class="backlog-spec-editor__raw-preview">${escHtml(content)}</pre>`;
            return;
        }

        preview.innerHTML = PGMarkdown.render(content);
    }

    function _renderSpecEditorWorkspace() {
        if (!specEditorState || !currentItem) return;
        const main = document.getElementById('mainContent');
        const codeOrTitle = currentItem.code || currentItem.title;

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([
                    { label: 'Backlog', onclick: 'BacklogView.render()' },
                    { label: escHtml(codeOrTitle), onclick: 'BacklogView.closeSpecEditor()' },
                    { label: `${escHtml(specEditorState.label)} Editor` },
                ])}
                <div class="backlog-detail-header">
                    <div class="backlog-detail-header__title-row">
                        ${PGStatusRegistry.badge(specEditorState.status, { label: STATUS_LABELS[currentItem.status] || currentItem.status })}
                        <h2 class="pg-view-title" id="specEditorWorkspaceTitle">${escHtml(specEditorState.title || specEditorState.label)}</h2>
                    </div>
                    <div class="backlog-detail-header__actions">
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.closeSpecEditor()">← Back to Specs</button>
                        <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="BacklogView.printSpec('${specEditorState.specType}', ${specEditorState.specId}, '${escHtml(specEditorState.title || specEditorState.label)}')">Print / PDF</button>
                        <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="BacklogView.downloadSpec('${specEditorState.specType}', ${specEditorState.specId}, '${escHtml(specEditorState.title || specEditorState.label)}')">Download</button>
                        <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="BacklogView.saveSpec('${specEditorState.specType}', ${specEditorState.specId})">Save</button>
                    </div>
                </div>
            </div>

            <div class="backlog-spec-editor-workspace">
                <aside class="backlog-spec-editor-workspace__nav">
                    <div class="backlog-spec-editor__panel backlog-spec-editor__panel--nav">
                        <div class="backlog-spec-editor__section-head">
                            <div>
                                <p class="backlog-spec-content__eyebrow">Document Map</p>
                                <h3>${escHtml(specEditorState.label)}</h3>
                            </div>
                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="BacklogView.addSpecEditorSection()">+ Add</button>
                        </div>
                        <div id="specEditorNav" class="backlog-spec-editor__nav"></div>
                    </div>
                </aside>

                <section class="backlog-spec-editor-workspace__form">
                    <div id="specEditorPanel" class="backlog-spec-editor__panel"></div>
                </section>

                <aside class="backlog-spec-editor-workspace__preview">
                    <div class="backlog-spec-content backlog-spec-content--workspace">
                        <div class="backlog-spec-content__header">
                            <div>
                                <p class="backlog-spec-content__eyebrow">Live Preview</p>
                                <h4>${escHtml(specEditorState.label)}</h4>
                            </div>
                            <div class="backlog-spec-editor__preview-switch">
                                <button class="backlog-spec-editor__preview-btn ${specEditorState.previewMode === 'rendered' ? 'active' : ''}" onclick="BacklogView.setSpecEditorPreviewMode('rendered')">Preview</button>
                                <button class="backlog-spec-editor__preview-btn ${specEditorState.previewMode === 'markdown' ? 'active' : ''}" onclick="BacklogView.setSpecEditorPreviewMode('markdown')">Markdown</button>
                            </div>
                        </div>
                        <div id="specEditorPreview" class="backlog-spec-content__body backlog-spec-markdown"></div>
                    </div>
                </aside>
            </div>
        `;

        _renderSpecEditorNav();
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    async function editSpec(specType, specId) {
        const spec = _getSpecFromCurrentItem(specType);
        if (!spec) return;
        specEditorState = _buildSpecEditorState(specType, specId);
        _renderSpecEditorWorkspace();
    }

    async function saveSpec(specType, specId) {
        const endpoint = specType === 'fs'
            ? `/functional-specs/${specId}`
            : `/technical-specs/${specId}`;

        const isWorkspaceEditor = Boolean(specEditorState && specEditorState.specType === specType && specEditorState.specId === specId);
        const payload = isWorkspaceEditor
            ? {
                title: specEditorState.title,
                author: specEditorState.author,
                reviewer: specEditorState.reviewer,
                content: _serializeSpecEditorContent(),
            }
            : {
                title: document.getElementById('specTitle').value,
                author: document.getElementById('specAuthor').value,
                reviewer: document.getElementById('specReviewer').value,
                content: document.getElementById('specContent').value,
            };

        try {
            await API.put(endpoint, payload);
            App.toast('Spec saved', 'success');

            if (isWorkspaceEditor) {
                const activePanel = specEditorState.activePanel;
                const previewMode = specEditorState.previewMode;
                currentItem = await API.get(`/backlog/${currentItem.id}?include_specs=true`);
                specEditorState = _buildSpecEditorState(specType, specId);
                specEditorState.activePanel = activePanel === 'meta' || specEditorState.sections.some((section) => section.id === activePanel)
                    ? activePanel
                    : 'meta';
                specEditorState.previewMode = previewMode;
                _renderSpecEditorWorkspace();
                return;
            }

            App.closeModal();
            await openDetail(currentItem.id);
            switchDetailTab('specs');
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function closeSpecEditor() {
        specEditorState = null;
        renderDetail();
        switchDetailTab('specs');
    }

    function selectSpecEditorPanel(panelId) {
        if (!specEditorState) return;
        specEditorState.activePanel = panelId;
        _renderSpecEditorNav();
        _renderSpecEditorPanel();
    }

    function setSpecEditorPreviewMode(mode) {
        if (!specEditorState) return;
        specEditorState.previewMode = mode;
        _renderSpecEditorWorkspace();
    }

    function updateSpecEditorField(field, value) {
        if (!specEditorState) return;
        specEditorState[field] = value;
        _renderSpecEditorPreview();
    }

    function updateSpecEditorPreamble(value) {
        if (!specEditorState) return;
        specEditorState.preamble = value;
        _renderSpecEditorPreview();
    }

    function updateSpecEditorSectionTitle(index, value) {
        if (!specEditorState?.sections[index]) return;
        specEditorState.sections[index].title = value;
        _renderSpecEditorNav();
        _renderSpecEditorPreview();
    }

    function updateSpecEditorSectionBody(index, value) {
        if (!specEditorState?.sections[index]) return;
        specEditorState.sections[index].body = value;
        _renderSpecEditorPreview();
    }

    function updateStructuredSpecRow(sectionIndex, rowIndex, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;

        const config = _getStructuredSpecSectionConfig(section.title);
        if (!config) return;

        const parsed = _parseSectionTableBlock(section.body, config.fallbackRows);
        const nextRows = parsed.rows.map((row, index) => (index === rowIndex ? [row[0], value] : row));
        section.body = _buildStructuredSectionBody(parsed, nextRows, parsed.after);
        _renderSpecEditorPreview();
    }

    function updateStructuredSpecExtra(sectionIndex, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;

        const config = _getStructuredSpecSectionConfig(section.title);
        if (!config) return;

        const parsed = _parseSectionTableBlock(section.body, config.fallbackRows);
        section.body = _buildStructuredSectionBody(parsed, parsed.rows, value);
        _renderSpecEditorPreview();
    }

    function updateBusinessContextField(sectionIndex, field, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseBusinessContextSection(section.body);
        if (field === 'purpose' || field === 'extra') parsed[field] = value;
        else if (field === 'inScope' || field === 'outScope') parsed[field] = _parseListTextarea(value);
        section.body = _stringifyBusinessContextSection(parsed);
        _renderSpecEditorPreview();
    }

    function updateSolutionOverviewField(sectionIndex, field, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseSolutionOverviewSection(section.body);
        if (field === 'purpose' || field === 'extra') parsed[field] = value;
        else if (field === 'components') parsed[field] = _parseListTextarea(value);
        section.body = _stringifySolutionOverviewSection(parsed);
        _renderSpecEditorPreview();
    }

    function updateTestScenarioField(sectionIndex, field, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseTestScenariosSection(section.body);
        parsed[field] = value;
        section.body = _stringifyTestScenariosSection(parsed);
        _renderSpecEditorPreview();
    }

    function updateTestScenarioEntry(sectionIndex, scenarioIndex, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseTestScenariosSection(section.body);
        while (parsed.scenarios.length <= scenarioIndex) parsed.scenarios.push('');
        parsed.scenarios[scenarioIndex] = value;
        section.body = _stringifyTestScenariosSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function addTestScenarioEntry(sectionIndex) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseTestScenariosSection(section.body);
        parsed.scenarios.push('');
        section.body = _stringifyTestScenariosSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function removeTestScenarioEntry(sectionIndex, scenarioIndex) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseTestScenariosSection(section.body);
        parsed.scenarios = parsed.scenarios.filter((_, index) => index !== scenarioIndex);
        if (!parsed.scenarios.length) parsed.scenarios.push('');
        section.body = _stringifyTestScenariosSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function updateAssumptionDependencyField(sectionIndex, entryIndex, field, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseAssumptionsDependenciesSection(section.body);
        while (parsed.entries.length <= entryIndex) {
            parsed.entries.push({ type: 'Assumption', description: '', owner: '', status: 'Open' });
        }
        parsed.entries[entryIndex][field] = value;
        section.body = _stringifyAssumptionsDependenciesSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function updateAssumptionDependencyExtra(sectionIndex, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseAssumptionsDependenciesSection(section.body);
        parsed.after = value;
        section.body = _stringifyAssumptionsDependenciesSection(parsed);
        _renderSpecEditorPreview();
    }

    function addAssumptionDependencyEntry(sectionIndex) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseAssumptionsDependenciesSection(section.body);
        parsed.entries.push({ type: 'Dependency', description: '', owner: '', status: 'Open' });
        section.body = _stringifyAssumptionsDependenciesSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function removeAssumptionDependencyEntry(sectionIndex, entryIndex) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseAssumptionsDependenciesSection(section.body);
        parsed.entries = parsed.entries.filter((_, index) => index !== entryIndex);
        if (!parsed.entries.length) parsed.entries.push({ type: 'Assumption', description: '', owner: '', status: 'Open' });
        section.body = _stringifyAssumptionsDependenciesSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function updateOpenPointRiskField(sectionIndex, entryIndex, field, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseOpenPointsRisksSection(section.body);
        while (parsed.entries.length <= entryIndex) {
            parsed.entries.push({ number: String(parsed.entries.length + 1), description: '', owner: '', dueDate: '', type: 'Open Point / Risk', status: 'Open' });
        }
        parsed.entries[entryIndex][field] = value;
        section.body = _stringifyOpenPointsRisksSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function updateOpenPointRiskExtra(sectionIndex, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseOpenPointsRisksSection(section.body);
        parsed.after = value;
        section.body = _stringifyOpenPointsRisksSection(parsed);
        _renderSpecEditorPreview();
    }

    function addOpenPointRiskEntry(sectionIndex) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseOpenPointsRisksSection(section.body);
        parsed.entries.push({
            number: String(parsed.entries.length + 1),
            description: '',
            owner: '',
            dueDate: '',
            type: 'Open Point / Risk',
            status: 'Open',
        });
        section.body = _stringifyOpenPointsRisksSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function removeOpenPointRiskEntry(sectionIndex, entryIndex) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseOpenPointsRisksSection(section.body);
        parsed.entries = parsed.entries.filter((_, index) => index !== entryIndex);
        if (!parsed.entries.length) {
            parsed.entries.push({ number: '1', description: '', owner: '', dueDate: '', type: 'Open Point / Risk', status: 'Open' });
        } else {
            parsed.entries = parsed.entries.map((entry, index) => ({
                ...entry,
                number: entry.number || String(index + 1),
            }));
        }
        section.body = _stringifyOpenPointsRisksSection(parsed);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function updateGenericTableCell(sectionIndex, rowIndex, columnIndex, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseSectionTableBlock(section.body, []);
        const nextRows = (parsed.rows.length ? parsed.rows : [_buildGenericTableDefaultRow(parsed.header, 0)]).map((row, index) => {
            if (index !== rowIndex) return row;
            const nextRow = [...row];
            while (nextRow.length < parsed.header.length) nextRow.push('');
            nextRow[columnIndex] = value;
            return nextRow;
        });
        section.body = _buildStructuredSectionBody(parsed, nextRows, parsed.after);
        _renderSpecEditorPreview();
    }

    function updateGenericTableBefore(sectionIndex, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseSectionTableBlock(section.body, []);
        parsed.before = value;
        section.body = _buildStructuredSectionBody(parsed, parsed.rows.length ? parsed.rows : [_buildGenericTableDefaultRow(parsed.header, 0)], parsed.after);
        _renderSpecEditorPreview();
    }

    function updateGenericTableAfter(sectionIndex, value) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseSectionTableBlock(section.body, []);
        section.body = _buildStructuredSectionBody(parsed, parsed.rows.length ? parsed.rows : [_buildGenericTableDefaultRow(parsed.header, 0)], value);
        _renderSpecEditorPreview();
    }

    function addGenericTableRow(sectionIndex) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseSectionTableBlock(section.body, []);
        const nextRows = parsed.rows.length ? [...parsed.rows] : [];
        nextRows.push(_buildGenericTableDefaultRow(parsed.header, nextRows.length));
        section.body = _buildStructuredSectionBody(parsed, nextRows, parsed.after);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function removeGenericTableRow(sectionIndex, rowIndex) {
        const section = specEditorState?.sections[sectionIndex];
        if (!section) return;
        const parsed = _parseSectionTableBlock(section.body, []);
        let nextRows = parsed.rows.filter((_, index) => index !== rowIndex);
        if (!nextRows.length) nextRows = [_buildGenericTableDefaultRow(parsed.header, 0)];
        section.body = _buildStructuredSectionBody(parsed, nextRows, parsed.after);
        _renderSpecEditorPanel();
        _renderSpecEditorPreview();
    }

    function addSpecEditorSection() {
        if (!specEditorState) return;
        const nextIndex = specEditorState.sections.length + 1;
        const title = `New Section ${nextIndex}`;
        const section = {
            id: _slugifySpecSection(title, nextIndex),
            title,
            body: '',
        };
        specEditorState.sections.push(section);
        specEditorState.activePanel = section.id;
        _renderSpecEditorWorkspace();
    }

    function updateSpecPreview() {
        if (specEditorState) {
            _renderSpecEditorPreview();
            return;
        }
        const textarea = document.getElementById('specContent');
        const preview = document.getElementById('specPreview');
        if (!textarea || !preview) return;
        preview.innerHTML = PGMarkdown.render(textarea.value || '');
    }

    // Public API
    return {
        render, switchTab, renderDetail, applyListFilter, setListSearch, onListFilterChange,
        clearListFilter, clearAllListFilters,
        setConfigSearch, onConfigFilterChange, applyConfigFilter,
        showCreateModal, showCreateSelector, createWricefFromSelector,
        createConfigFromSelector, showEditModal, cancelInlineEdit, saveItem,
        openDetail, deleteItem, deleteItemConfirmed, switchDetailTab,
        showMoveModal, doMove, applyQuickMove,
        onOverviewPlanningChange, applyOverviewPlanning, applyOverviewStatus,
        showStats,
        showCreateSprintModal, showEditSprintModal, saveSprint, deleteSprint, deleteSprintConfirmed,
        showCreateConfigModal, showEditConfigModal, saveConfigItem, deleteConfigItem, deleteConfigItemConfirmed,
        openConfigDetail, applyConfigQuickMove, updateQuickMoveHint,
        updateSpecStatus, downloadSpec, printSpec, editSpec, saveSpec,
        closeSpecEditor, selectSpecEditorPanel, setSpecEditorPreviewMode,
        updateSpecEditorField, updateSpecEditorPreamble, updateSpecEditorSectionTitle, updateSpecEditorSectionBody,
        updateStructuredSpecRow, updateStructuredSpecExtra,
        updateGenericTableCell, updateGenericTableBefore, updateGenericTableAfter, addGenericTableRow, removeGenericTableRow,
        updateAssumptionDependencyField, updateAssumptionDependencyExtra, addAssumptionDependencyEntry, removeAssumptionDependencyEntry,
        updateBusinessContextField, updateSolutionOverviewField, updateTestScenarioField, updateTestScenarioEntry, addTestScenarioEntry, removeTestScenarioEntry,
        updateOpenPointRiskField, updateOpenPointRiskExtra, addOpenPointRiskEntry, removeOpenPointRiskEntry,
        addSpecEditorSection, updateSpecPreview,
        showAIWricefSpecModal, runAIWricefSpec,
        _generateSpecs,
    };
})();
