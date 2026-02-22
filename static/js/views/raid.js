/**
 * SAP Transformation Platform — RAID View (Sprint 6)
 *
 * Dashboard with risk heatmap, RAID stats, action aging
 * + tabbed list views (Risks / Actions / Issues / Decisions) with filters
 * + detail modals for create/edit
 */
const RaidView = (() => {
    let _programId = null;
    let _currentTab = 'risks';
    let _filters = {};
    let _searchQuery = '';
    let _allItems = [];

    // ── Main Render ──────────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        _programId = prog ? prog.id : null;

        if (!_programId) {
            main.innerHTML = PGEmptyState.html({ icon: 'raid', title: 'RAID Log', description: 'Devam etmek için önce bir program seç.', action: { label: 'Programlara Git', onclick: "App.navigate('programs')" } });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{label:'Programs',onclick:'App.navigate("programs")'},{label:'RAID Log'}])}
                <h2 class="pg-view-title">RAID Log</h2>
            </div>
            <div class="page-header" style="margin-bottom:20px">
                <div>
                    <p style="color:var(--pg-color-text-secondary);margin:0;font-size:13px">Risks, Actions, Issues &amp; Decisions</p>
                </div>
                <div class="page-header__actions">
                    <div style="position:relative;display:inline-block" id="raidNewBtnWrap">
                        ${ExpUI.actionButton({ label: '+ New', variant: 'primary', size: 'md', onclick: 'RaidView.toggleNewMenu()' })}
                        <div class="raid-new-menu" id="raidNewMenu" style="display:none">
                            <div class="raid-new-menu__item" onclick="RaidView.openCreate('risk')">
                                <span style="color:#dc2626">●</span> Risk
                            </div>
                            <div class="raid-new-menu__item" onclick="RaidView.openCreate('action')">
                                <span style="color:#3b82f6">●</span> Action
                            </div>
                            <div class="raid-new-menu__item" onclick="RaidView.openCreate('issue')">
                                <span style="color:#f59e0b">●</span> Issue
                            </div>
                            <div class="raid-new-menu__item" onclick="RaidView.openCreate('decision')">
                                <span style="color:#8b5cf6">●</span> Decision
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="raid-dash-row" id="raidDashRow">
                <div id="raidStats"></div>
                <div class="card" style="padding:16px" id="riskHeatmapCard">
                    <div style="font-size:13px;font-weight:600;color:#64748b;margin-bottom:8px">Risk Heatmap</div>
                    <div id="riskHeatmap" style="overflow-x:auto"></div>
                </div>
            </div>

            <div class="tabs" style="margin-bottom:12px">
                <button class="tab-btn active" data-tab="risks" onclick="RaidView.switchTab('risks')">
                    <span style="color:#dc2626">●</span> Risks
                </button>
                <button class="tab-btn" data-tab="actions" onclick="RaidView.switchTab('actions')">
                    <span style="color:#3b82f6">●</span> Actions
                </button>
                <button class="tab-btn" data-tab="issues" onclick="RaidView.switchTab('issues')">
                    <span style="color:#f59e0b">●</span> Issues
                </button>
                <button class="tab-btn" data-tab="decisions" onclick="RaidView.switchTab('decisions')">
                    <span style="color:#8b5cf6">●</span> Decisions
                </button>
            </div>

            <div id="raidFilterBar"></div>
            <div id="raidListContainer"></div>
        `;

        await Promise.all([loadStats(), loadHeatmap(), loadList('risks')]);
    }

    // ── Stats ────────────────────────────────────────────────────────────
    async function loadStats() {
        try {
            const s = await API.get(`/programs/${_programId}/raid/stats`);
            document.getElementById('raidStats').innerHTML = `
                <div class="exp-kpi-strip">
                    ${ExpUI.kpiBlock({ value: s.risks.open, label: 'Open Risks', accent: '#dc2626', sub: s.risks.critical > 0 ? s.risks.critical + ' critical' : '' })}
                    ${ExpUI.kpiBlock({ value: s.actions.open, label: 'Open Actions', accent: '#3b82f6', sub: s.actions.overdue > 0 ? s.actions.overdue + ' overdue' : '' })}
                    ${ExpUI.kpiBlock({ value: s.issues.open, label: 'Open Issues', accent: '#f59e0b', sub: s.issues.critical > 0 ? s.issues.critical + ' critical' : '' })}
                    ${ExpUI.kpiBlock({ value: s.decisions.pending, label: 'Pending Decisions', accent: '#8b5cf6', sub: s.decisions.total + ' total' })}
                </div>
            `;
        } catch (e) {
            document.getElementById('raidStats').innerHTML =
                `<p class="text-muted">⚠️ Stats unavailable</p>`;
        }
    }

    // ── Heatmap ──────────────────────────────────────────────────────────
    async function loadHeatmap() {
        try {
            const h = await API.get(`/programs/${_programId}/raid/heatmap`);
            const impLabels = ['Neg', 'Min', 'Mod', 'Maj', 'Sev'];
            const probLabels = ['VL', 'Low', 'Med', 'High', 'VH'];

            let html = '<table class="heatmap-table heatmap-table--compact"><thead><tr><th></th>';
            impLabels.forEach(l => { html += `<th>${l}</th>`; });
            html += '</tr></thead><tbody>';

            for (let p = 4; p >= 0; p--) {
                html += `<tr><th>${probLabels[p]}</th>`;
                for (let i = 0; i < 5; i++) {
                    const cell = h.matrix[p][i];
                    const score = (p + 1) * (i + 1);
                    const bg = score <= 3 ? '#dcfce7'
                        : score <= 6 ? '#fef9c3'
                        : score <= 12 ? '#fed7aa'
                        : score <= 16 ? '#fecaca'
                        : '#fca5a5';

                    const hasRisks = cell.length > 0;
                    html += `<td class="heatmap-cell${hasRisks ? ' heatmap-cell--clickable' : ''}"
                              style="background:${bg}"
                              title="${hasRisks ? cell.map(r => r.code + ': ' + r.title).join('\n') : 'Score: ' + score}"
                              ${hasRisks ? `onclick="RaidView.showHeatmapCell(${JSON.stringify(cell).replace(/"/g, '&quot;')})"` : ''}>
                        ${hasRisks ? `<span class="heatmap-cell__count">${cell.length}</span>` : ''}
                    </td>`;
                }
                html += '</tr>';
            }
            html += '</tbody></table>';
            document.getElementById('riskHeatmap').innerHTML = html;
        } catch (e) {
            document.getElementById('riskHeatmap').innerHTML =
                `<p class="text-muted">No heatmap data</p>`;
        }
    }

    function toggleNewMenu() {
        const menu = document.getElementById('raidNewMenu');
        if (!menu) return;
        const isOpen = menu.style.display !== 'none';
        menu.style.display = isOpen ? 'none' : 'block';
        if (!isOpen) {
            setTimeout(() => {
                const handler = (e) => {
                    if (!e.target.closest('#raidNewBtnWrap')) {
                        menu.style.display = 'none';
                        document.removeEventListener('click', handler);
                    }
                };
                document.addEventListener('click', handler);
            }, 10);
        }
    }

    function showHeatmapCell(risks) {
        const html = `<div class="modal">
            <div class="modal__header"><h3>Risks in Cell</h3>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal__body">
                <table class="table"><thead><tr><th>Code</th><th>Title</th><th>RAG</th></tr></thead>
                <tbody>${risks.map(r => `<tr><td>${r.code}</td><td>${r.title}</td>
                    <td>${PGStatusRegistry.badge(r.rag_status)}</td></tr>`).join('')}
                </tbody></table>
            </div>
        </div>`;
        App.openModal(html);
    }

    // ── List Views ───────────────────────────────────────────────────────
    function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('.tabs .tab-btn').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        loadList(tab);
    }

    async function loadList(tab) {
        const container = document.getElementById('raidListContainer');
        _filters = {};
        _searchQuery = '';
        try {
            let items = [];
            if (tab === 'risks') items = await API.get(`/programs/${_programId}/risks`);
            else if (tab === 'actions') items = await API.get(`/programs/${_programId}/actions`);
            else if (tab === 'issues') items = await API.get(`/programs/${_programId}/issues`);
            else if (tab === 'decisions') items = await API.get(`/programs/${_programId}/decisions`);

            _allItems = Array.isArray(items) ? items : (items.items || []);
            renderFilterBar(tab);

            if (!_allItems.length) {
                container.innerHTML = PGEmptyState.html({ icon: 'raid', title: `${tab.charAt(0).toUpperCase() + tab.slice(1)} bulunamadı` });
                return;
            }
            container.innerHTML = renderTable(tab, _allItems);
            const countEl = document.getElementById('raidItemCount');
            if (countEl) countEl.textContent = `${_allItems.length} items`;
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
        }
    }

    function renderFilterBar(tab) {
        const filterDefs = {
            risks: [
                { id: 'status', label: 'Status', icon: '📋', type: 'multi',
                    options: [
                        { value: 'identified', label: 'Identified' },
                        { value: 'analysed', label: 'Analysed' },
                        { value: 'mitigating', label: 'Mitigating' },
                        { value: 'closed', label: 'Closed' },
                        { value: 'accepted', label: 'Accepted' },
                    ],
                    selected: _filters.status || [], color: '#3b82f6',
                },
                { id: 'priority', label: 'Priority', icon: '⚡', type: 'multi',
                    options: [
                        { value: 'critical', label: 'Critical' },
                        { value: 'high', label: 'High' },
                        { value: 'medium', label: 'Medium' },
                        { value: 'low', label: 'Low' },
                    ],
                    selected: _filters.priority || [], color: '#dc2626',
                },
                { id: 'rag_status', label: 'RAG', icon: '🚦', type: 'single',
                    options: [
                        { value: 'red', label: '🔴 Red' },
                        { value: 'orange', label: '🟠 Orange' },
                        { value: 'amber', label: '🟡 Amber' },
                        { value: 'green', label: '🟢 Green' },
                    ],
                    selected: _filters.rag_status || '', color: '#f59e0b',
                },
            ],
            actions: [
                { id: 'status', label: 'Status', icon: '📋', type: 'multi',
                    options: [
                        { value: 'open', label: 'Open' },
                        { value: 'in_progress', label: 'In Progress' },
                        { value: 'completed', label: 'Completed' },
                        { value: 'cancelled', label: 'Cancelled' },
                    ],
                    selected: _filters.status || [], color: '#3b82f6',
                },
                { id: 'priority', label: 'Priority', icon: '⚡', type: 'multi',
                    options: [
                        { value: 'critical', label: 'Critical' },
                        { value: 'high', label: 'High' },
                        { value: 'medium', label: 'Medium' },
                        { value: 'low', label: 'Low' },
                    ],
                    selected: _filters.priority || [], color: '#dc2626',
                },
                { id: 'action_type', label: 'Type', icon: '🔧', type: 'multi',
                    options: [
                        { value: 'preventive', label: 'Preventive' },
                        { value: 'corrective', label: 'Corrective' },
                        { value: 'detective', label: 'Detective' },
                        { value: 'improvement', label: 'Improvement' },
                    ],
                    selected: _filters.action_type || [], color: '#8b5cf6',
                },
            ],
            issues: [
                { id: 'status', label: 'Status', icon: '📋', type: 'multi',
                    options: [
                        { value: 'open', label: 'Open' },
                        { value: 'in_progress', label: 'In Progress' },
                        { value: 'resolved', label: 'Resolved' },
                        { value: 'closed', label: 'Closed' },
                    ],
                    selected: _filters.status || [], color: '#f59e0b',
                },
                { id: 'severity', label: 'Severity', icon: '🔥', type: 'multi',
                    options: [
                        { value: 'critical', label: 'Critical' },
                        { value: 'major', label: 'Major' },
                        { value: 'moderate', label: 'Moderate' },
                        { value: 'minor', label: 'Minor' },
                    ],
                    selected: _filters.severity || [], color: '#dc2626',
                },
            ],
            decisions: [
                { id: 'status', label: 'Status', icon: '📋', type: 'multi',
                    options: [
                        { value: 'pending', label: 'Pending' },
                        { value: 'approved', label: 'Approved' },
                        { value: 'rejected', label: 'Rejected' },
                        { value: 'deferred', label: 'Deferred' },
                    ],
                    selected: _filters.status || [], color: '#8b5cf6',
                },
            ],
        };

        const fbContainer = document.getElementById('raidFilterBar');
        if (!fbContainer) return;
        fbContainer.innerHTML = ExpUI.filterBar({
            id: 'raidFB',
            searchPlaceholder: `Search ${tab}…`,
            searchValue: _searchQuery,
            onSearch: "RaidView.setSearch(this.value)",
            onChange: "RaidView.onFilterBarChange",
            filters: filterDefs[tab] || [],
            actionsHtml: `
                <span style="font-size:12px;color:#94a3b8" id="raidItemCount"></span>
            `,
        });
    }

    function setSearch(val) {
        _searchQuery = val;
        applyFiltersAndRender();
    }

    function onFilterBarChange(update) {
        if (update._clearAll) {
            _filters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete _filters[key];
                } else {
                    _filters[key] = val;
                }
            });
        }
        renderFilterBar(_currentTab);
        applyFiltersAndRender();
    }

    function applyFiltersAndRender() {
        let items = [..._allItems];

        if (_searchQuery) {
            const q = _searchQuery.toLowerCase();
            items = items.filter(it =>
                (it.title || '').toLowerCase().includes(q) ||
                (it.code || '').toLowerCase().includes(q) ||
                (it.owner || '').toLowerCase().includes(q) ||
                (it.description || '').toLowerCase().includes(q)
            );
        }

        Object.entries(_filters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (!values.length) return;
            items = items.filter(it => values.includes(String(it[key])));
        });

        const container = document.getElementById('raidListContainer');
        const countEl = document.getElementById('raidItemCount');
        if (countEl) countEl.textContent = `${items.length} of ${_allItems.length}`;

        if (!items.length) {
            container.innerHTML = PGEmptyState.html({ icon: 'raid', title: `Filtreyle eşleşen ${_currentTab} yok` });
            return;
        }
        container.innerHTML = renderTable(_currentTab, items);
    }

    function renderTable(tab, items) {
        const ragDot = (rag) => {
            const colors = { red: '#dc2626', orange: '#f97316', amber: '#f59e0b', green: '#22c55e' };
            const labels = { red: 'Critical', orange: 'High', amber: 'Medium', green: 'Low' };
            return `<span style="display:inline-flex;align-items:center;gap:4px">
                <span style="width:8px;height:8px;border-radius:50%;background:${colors[rag] || '#94a3b8'}"></span>
                <span style="font-size:12px">${labels[rag] || rag || '—'}</span>
            </span>`;
        };

        const scoreBadge = (score) => {
            if (score == null) return '—';
            const bg = score >= 16 ? '#fee2e2' : score >= 10 ? '#fef3c7' : score >= 5 ? '#f0fdf4' : '#f8fafc';
            const color = score >= 16 ? '#991b1b' : score >= 10 ? '#92400e' : score >= 5 ? '#166534' : '#64748b';
            return `<span style="display:inline-flex;align-items:center;justify-content:center;min-width:28px;height:22px;border-radius:4px;background:${bg};color:${color};font-size:12px;font-weight:700">${score}</span>`;
        };

        const statusBadge = (status) => PGStatusRegistry.badge(status);
        const priorityBadge = (priority) => PGStatusRegistry.badge(priority);

        const colDefs = {
            risks: [
                { key: 'code', label: 'Code', width: '90px', render: v => `<code style="font-size:12px;color:#475569">${v}</code>` },
                { key: 'title', label: 'Title', width: '', render: v => `<span style="font-weight:500">${v}</span>` },
                { key: 'status', label: 'Status', width: '100px', render: statusBadge },
                { key: 'priority', label: 'Priority', width: '95px', render: priorityBadge },
                { key: 'risk_score', label: 'Score', width: '60px', render: scoreBadge },
                { key: 'rag_status', label: 'RAG', width: '80px', render: ragDot },
                { key: 'owner', label: 'Owner', width: '120px', render: v => `<span style="font-size:12px;color:#64748b">${v || '—'}</span>` },
            ],
            actions: [
                { key: 'code', label: 'Code', width: '90px', render: v => `<code style="font-size:12px;color:#475569">${v}</code>` },
                { key: 'title', label: 'Title', width: '', render: v => `<span style="font-weight:500">${v}</span>` },
                { key: 'status', label: 'Status', width: '100px', render: statusBadge },
                { key: 'priority', label: 'Priority', width: '95px', render: priorityBadge },
                { key: 'action_type', label: 'Type', width: '90px', render: v => statusBadge(v) },
                { key: 'due_date', label: 'Due', width: '90px', render: v => {
                    if (!v) return '—';
                    const d = new Date(v);
                    const isOverdue = d < new Date();
                    return `<span style="font-size:12px;${isOverdue ? 'color:#dc2626;font-weight:600' : 'color:#64748b'}">${v}</span>`;
                }},
                { key: 'owner', label: 'Owner', width: '120px', render: v => `<span style="font-size:12px;color:#64748b">${v || '—'}</span>` },
            ],
            issues: [
                { key: 'code', label: 'Code', width: '90px', render: v => `<code style="font-size:12px;color:#475569">${v}</code>` },
                { key: 'title', label: 'Title', width: '', render: v => `<span style="font-weight:500">${v}</span>` },
                { key: 'status', label: 'Status', width: '100px', render: statusBadge },
                { key: 'severity', label: 'Severity', width: '85px', render: priorityBadge },
                { key: 'priority', label: 'Priority', width: '95px', render: priorityBadge },
                { key: 'owner', label: 'Owner', width: '120px', render: v => `<span style="font-size:12px;color:#64748b">${v || '—'}</span>` },
            ],
            decisions: [
                { key: 'code', label: 'Code', width: '90px', render: v => `<code style="font-size:12px;color:#475569">${v}</code>` },
                { key: 'title', label: 'Title', width: '', render: v => `<span style="font-weight:500">${v}</span>` },
                { key: 'status', label: 'Status', width: '100px', render: statusBadge },
                { key: 'priority', label: 'Priority', width: '95px', render: priorityBadge },
                { key: 'decision_owner', label: 'Owner', width: '120px', render: v => `<span style="font-size:12px;color:#64748b">${v || '—'}</span>` },
                { key: 'reversible', label: 'Reversible', width: '75px', render: v => v ? '✅' : '❌' },
            ],
        };

        const cols = colDefs[tab] || colDefs.risks;
        let html = '<table class="data-table" style="font-size:13px"><thead><tr>';
        cols.forEach(c => {
            html += `<th style="${c.width ? 'width:' + c.width : ''}">${c.label}</th>`;
        });
        html += '<th style="width:70px;text-align:right"></th></tr></thead><tbody>';

        items.forEach(item => {
            html += `<tr style="cursor:pointer" onclick="RaidView.openDetail('${tab}', ${item.id})">`;
            cols.forEach(c => {
                html += `<td>${c.render(item[c.key])}</td>`;
            });
            html += `<td style="text-align:right" onclick="event.stopPropagation()">
                <button class="btn-icon" onclick="RaidView.openEdit('${tab}', ${item.id})" title="Edit">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
                </button>
                <button class="btn-icon btn-icon--danger" onclick="RaidView.deleteItem('${tab}', ${item.id})" title="Delete">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
                </button>
            </td></tr>`;
        });
        html += '</tbody></table>';
        return html;
    }

    // ── Detail Modal ─────────────────────────────────────────────────────
    async function openDetail(tab, id) {
        const singular = tab.slice(0, -1);  // risks → risk
        try {
            const item = await API.get(`/${tab}/${id}`);
            const fields = Object.entries(item)
                .filter(([k]) => !['id', 'raid_type', 'program_id'].includes(k))
                .map(([k, v]) => {
                    const label = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    return `<tr><td><strong>${label}</strong></td><td>${v ?? '-'}</td></tr>`;
                }).join('');

            App.openModal(`
                <div class="modal">
                    <div class="modal__header">
                        <h3>${item.code} — ${item.title}</h3>
                        <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
                    </div>
                    <div class="modal__body">
                        <table class="table">${fields}</table>
                    </div>
                    <div class="modal__footer">
                        <button class="btn btn-primary" onclick="RaidView.openEdit('${tab}', ${id})">Edit</button>
                        <button class="btn" onclick="App.closeModal()">Close</button>
                    </div>
                </div>
            `);
        } catch (e) {
            App.toast(`Error loading ${singular}: ${e.message}`, 'error');
        }
    }

    // ── Create / Edit Forms ──────────────────────────────────────────────
    async function openCreate(type) {
        const title = type.charAt(0).toUpperCase() + type.slice(1);
        const formHtml = await _getForm(type, {});
        App.openModal(`
            <div class="modal">
                <div class="modal__header"><h3>New ${title}</h3>
                    <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
                </div>
                <div class="modal__body">
                    ${formHtml}
                </div>
                <div class="modal__footer">
                    <button class="btn btn-primary" onclick="RaidView.submitCreate('${type}')">Create</button>
                    <button class="btn" onclick="App.closeModal()">Cancel</button>
                </div>
            </div>
        `);
    }

    async function openEdit(tab, id) {
        const singular = tab.slice(0, -1);
        try {
            const item = await API.get(`/${tab}/${id}`);
            const formHtml = await _getForm(singular, item);
            App.openModal(`
                <div class="modal">
                    <div class="modal__header"><h3>Edit ${item.code}</h3>
                        <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
                    </div>
                    <div class="modal__body">
                        ${formHtml}
                    </div>
                    <div class="modal__footer">
                        <button class="btn btn-primary" onclick="RaidView.submitEdit('${tab}', ${id})">Save</button>
                        <button class="btn" onclick="App.closeModal()">Cancel</button>
                    </div>
                </div>
            `);
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function _getForm(type, data) {
        const v = (k) => data[k] || '';
        const members = await TeamMemberPicker.fetchMembers(_programId);
        const ownerHtml = TeamMemberPicker.renderSelect('rf_owner', members, data.owner_id || data.owner || '', { cssClass: 'form-control' });
        let common = `
            <div class="form-group"><label>Title *</label>
                <input id="rf_title" class="form-control" value="${v('title')}" required></div>
            <div class="form-group"><label>Description</label>
                <textarea id="rf_description" class="form-control" rows="3">${v('description')}</textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Owner</label>
                    ${ownerHtml}</div>
                <div class="form-group"><label>Priority</label>
                    <select id="rf_priority" class="form-control">
                        ${['low', 'medium', 'high', 'critical'].map(p =>
                            `<option value="${p}" ${v('priority') === p ? 'selected' : ''}>${p}</option>`
                        ).join('')}
                    </select></div>
            </div>
        `;

        if (type === 'risk') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Probability (1-5)</label>
                        <input id="rf_probability" type="number" min="1" max="5" class="form-control" value="${data.probability || 3}"></div>
                    <div class="form-group"><label>Impact (1-5)</label>
                        <input id="rf_impact" type="number" min="1" max="5" class="form-control" value="${data.impact || 3}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Category</label>
                        <select id="rf_risk_category" class="form-control">
                            ${['technical', 'organisational', 'commercial', 'external', 'schedule', 'resource', 'scope'].map(c =>
                                `<option value="${c}" ${v('risk_category') === c ? 'selected' : ''}>${c}</option>`
                            ).join('')}
                        </select></div>
                    <div class="form-group"><label>Response</label>
                        <select id="rf_risk_response" class="form-control">
                            ${['avoid', 'transfer', 'mitigate', 'accept', 'escalate'].map(r =>
                                `<option value="${r}" ${v('risk_response') === r ? 'selected' : ''}>${r}</option>`
                            ).join('')}
                        </select></div>
                </div>
                <div class="form-group"><label>Mitigation Plan</label>
                    <textarea id="rf_mitigation_plan" class="form-control" rows="2">${v('mitigation_plan')}</textarea></div>
                <div class="form-group"><label>Contingency Plan</label>
                    <textarea id="rf_contingency_plan" class="form-control" rows="2">${v('contingency_plan')}</textarea></div>
            `;
        } else if (type === 'action') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Due Date</label>
                        <input id="rf_due_date" type="date" class="form-control" value="${v('due_date')}"></div>
                    <div class="form-group"><label>Type</label>
                        <select id="rf_action_type" class="form-control">
                            ${['preventive', 'corrective', 'detective', 'improvement', 'follow_up'].map(t =>
                                `<option value="${t}" ${v('action_type') === t ? 'selected' : ''}>${t}</option>`
                            ).join('')}
                        </select></div>
                </div>
            `;
        } else if (type === 'issue') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Severity</label>
                        <select id="rf_severity" class="form-control">
                            ${['minor', 'moderate', 'major', 'critical'].map(s =>
                                `<option value="${s}" ${v('severity') === s ? 'selected' : ''}>${s}</option>`
                            ).join('')}
                        </select></div>
                    <div class="form-group"><label>Escalation Path</label>
                        <input id="rf_escalation_path" class="form-control" value="${v('escalation_path')}"></div>
                </div>
                <div class="form-group"><label>Root Cause</label>
                    <textarea id="rf_root_cause" class="form-control" rows="2">${v('root_cause')}</textarea></div>
            `;
        } else if (type === 'decision') {
            const decisionOwnerHtml = TeamMemberPicker.renderSelect('rf_decision_owner', members, data.decision_owner_id || data.decision_owner || '', { cssClass: 'form-control' });
            common += `
                <div class="form-group"><label>Decision Owner</label>
                    ${decisionOwnerHtml}</div>
                <div class="form-group"><label>Alternatives</label>
                    <textarea id="rf_alternatives" class="form-control" rows="2">${v('alternatives')}</textarea></div>
                <div class="form-group"><label>Rationale</label>
                    <textarea id="rf_rationale" class="form-control" rows="2">${v('rationale')}</textarea></div>
                <div class="form-group"><label>Reversible</label>
                    <select id="rf_reversible" class="form-control">
                        <option value="true" ${data.reversible !== false ? 'selected' : ''}>Yes</option>
                        <option value="false" ${data.reversible === false ? 'selected' : ''}>No</option>
                    </select></div>
            `;
        }
        return common;
    }

    function _collectFormData(type) {
        const data = {
            title: document.getElementById('rf_title')?.value || '',
            description: document.getElementById('rf_description')?.value || '',
            owner: document.getElementById('rf_owner')?.value || '',
            owner_id: document.getElementById('rf_owner')?.value || null,
            priority: document.getElementById('rf_priority')?.value || 'medium',
        };
        if (type === 'risk') {
            data.probability = parseInt(document.getElementById('rf_probability')?.value) || 3;
            data.impact = parseInt(document.getElementById('rf_impact')?.value) || 3;
            data.risk_category = document.getElementById('rf_risk_category')?.value || 'technical';
            data.risk_response = document.getElementById('rf_risk_response')?.value || 'mitigate';
            data.mitigation_plan = document.getElementById('rf_mitigation_plan')?.value || '';
            data.contingency_plan = document.getElementById('rf_contingency_plan')?.value || '';
        } else if (type === 'action') {
            data.due_date = document.getElementById('rf_due_date')?.value || null;
            data.action_type = document.getElementById('rf_action_type')?.value || 'corrective';
        } else if (type === 'issue') {
            data.severity = document.getElementById('rf_severity')?.value || 'moderate';
            data.escalation_path = document.getElementById('rf_escalation_path')?.value || '';
            data.root_cause = document.getElementById('rf_root_cause')?.value || '';
        } else if (type === 'decision') {
            data.decision_owner = document.getElementById('rf_decision_owner')?.value || '';
            data.decision_owner_id = document.getElementById('rf_decision_owner')?.value || null;
            data.alternatives = document.getElementById('rf_alternatives')?.value || '';
            data.rationale = document.getElementById('rf_rationale')?.value || '';
            data.reversible = document.getElementById('rf_reversible')?.value === 'true';
        }
        return data;
    }

    async function submitCreate(type) {
        const data = _collectFormData(type);
        if (!data.title) { App.toast('Title is required', 'error'); return; }
        try {
            await API.post(`/programs/${_programId}/${type}s`, data);
            App.closeModal();
            App.toast(`${type} created`, 'success');
            render();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function submitEdit(tab, id) {
        const singular = tab.slice(0, -1);
        const data = _collectFormData(singular);
        if (!data.title) { App.toast('Title is required', 'error'); return; }
        try {
            await API.put(`/${tab}/${id}`, data);
            App.closeModal();
            App.toast(`${singular} updated`, 'success');
            render();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function deleteItem(tab, id) {
        if (!confirm(`Delete this ${tab.slice(0, -1)}?`)) return;
        try {
            await API.delete(`/${tab}/${id}`);
            App.toast('Deleted', 'success');
            loadList(_currentTab);
            loadStats();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    // ── RAID Type Badge ──────────────────────────────────────────────────
    function _raidTypeBadge(type) {
        const LABELS = { R: 'Risk', A: 'Assumption', I: 'Issue', D: 'Dependency' };
        const KEYS   = { R: 'risk', A: 'assumption', I: 'issue', D: 'dependency' };
        return PGStatusRegistry.badge(KEYS[type] || type, { label: LABELS[type] || type });
    }

    // ── Public API ───────────────────────────────────────────────────────
    return {
        render, switchTab, openDetail, openCreate, openEdit,
        submitCreate, submitEdit, deleteItem, showHeatmapCell,
        toggleNewMenu, setSearch, onFilterBarChange,
        _raidTypeBadge,
    };
})();
