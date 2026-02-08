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

    // ── Main render ──────────────────────────────────────────────────────
    async function render() {
        currentItem = null;
        programId = _getSelectedProgramId();
        const main = document.getElementById('mainContent');

        if (!programId) {
            main.innerHTML = `
                <div class="page-header"><h1>Backlog (WRICEF)</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">⚙️</div>
                    <div class="empty-state__title">Select a Program</div>
                    <p>Choose a program from the header dropdown to view its backlog.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>Backlog (WRICEF)</h1>
                <div>
                    <button class="btn btn-secondary" onclick="BacklogView.showStats()">📈 Stats</button>
                    <button class="btn btn-primary" onclick="BacklogView.showCreateModal()">+ New Item</button>
                </div>
            </div>
            <div class="backlog-tabs">
                <button class="backlog-tab ${currentTab === 'board' ? 'active' : ''}" onclick="BacklogView.switchTab('board')">🗂️ Kanban Board</button>
                <button class="backlog-tab ${currentTab === 'list' ? 'active' : ''}" onclick="BacklogView.switchTab('list')">📋 WRICEF List</button>
                <button class="backlog-tab ${currentTab === 'config' ? 'active' : ''}" onclick="BacklogView.switchTab('config')">⚙️ Config Items</button>
                <button class="backlog-tab ${currentTab === 'sprints' ? 'active' : ''}" onclick="BacklogView.switchTab('sprints')">🏃 Sprints</button>
            </div>
            <div id="backlogContent">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>`;

        await loadData();
    }

    function _getSelectedProgramId() {
        const sel = document.getElementById('globalProjectSelector');
        return sel ? parseInt(sel.value) || null : null;
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
        document.querySelectorAll('.backlog-tab').forEach((t, idx) => {
            const tabs = ['board', 'list', 'config', 'sprints'];
            t.classList.toggle('active', tabs[idx] === tab);
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
        const visibleColumns = ['new', 'design', 'build', 'test', 'deploy', 'closed', 'blocked'];
        const summary = boardData.summary;

        c.innerHTML = `
            <div class="backlog-summary">
                <div class="backlog-kpi"><span>${summary.total_items}</span> Items</div>
                <div class="backlog-kpi"><span>${summary.total_points}</span> Points</div>
                <div class="backlog-kpi"><span>${summary.done_points}</span> Done</div>
                <div class="backlog-kpi"><span>${summary.completion_pct}%</span> Complete</div>
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
                <div class="empty-state">
                    <div class="empty-state__icon">⚙️</div>
                    <div class="empty-state__title">No backlog items yet</div>
                    <p>Create your first WRICEF item to build the development backlog.</p><br>
                    <button class="btn btn-primary" onclick="BacklogView.showCreateModal()">+ New Item</button>
                </div>`;
            return;
        }

        c.innerHTML = `
            <div class="card" style="margin-top:12px">
                <div class="backlog-filters">
                    <select id="blFilterType" onchange="BacklogView.applyListFilter()" class="form-input" style="width:auto">
                        <option value="">All Types</option>
                        ${Object.entries(WRICEF).map(([k, v]) => `<option value="${k}">${v.icon} ${v.label}</option>`).join('')}
                    </select>
                    <select id="blFilterStatus" onchange="BacklogView.applyListFilter()" class="form-input" style="width:auto">
                        <option value="">All Statuses</option>
                        ${Object.entries(STATUS_LABELS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
                    </select>
                    <select id="blFilterPriority" onchange="BacklogView.applyListFilter()" class="form-input" style="width:auto">
                        <option value="">All Priorities</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
                <table class="data-table" id="backlogTable">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Code</th>
                            <th>Title</th>
                            <th>Module</th>
                            <th>Status</th>
                            <th>Priority</th>
                            <th>SP</th>
                            <th>Assigned</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="backlogTableBody">
                        ${_renderTableRows(items)}
                    </tbody>
                </table>
            </div>`;
    }

    function _renderTableRows(list) {
        return list.map(i => {
            const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
            const linkCount = (i.requirement_id ? 1 : 0) +
                              (i.functional_spec ? 1 : 0) +
                              (i.technical_spec ? 1 : 0);
            return `
                <tr>
                    <td><span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label}</span></td>
                    <td><strong>${escHtml(i.code || '—')}</strong></td>
                    <td><a href="#" onclick="BacklogView.openDetail(${i.id});return false">${escHtml(i.title)}</a>
                        ${linkCount > 0 ? `<span class="trace-badge" title="${linkCount} linked items">🔗${linkCount}</span>` : ''}
                    </td>
                    <td>${escHtml(i.module || '—')}</td>
                    <td><span class="badge badge-${i.status}">${STATUS_LABELS[i.status] || i.status}</span></td>
                    <td><span class="badge badge-${i.priority}">${i.priority}</span></td>
                    <td>${i.story_points || '—'}</td>
                    <td>${escHtml(i.assigned_to || '—')}</td>
                    <td>
                        <button class="btn btn-danger btn-sm" onclick="event.stopPropagation();BacklogView.deleteItem(${i.id})">Delete</button>
                    </td>
                </tr>`;
        }).join('');
    }

    function applyListFilter() {
        const typeF = document.getElementById('blFilterType').value;
        const statusF = document.getElementById('blFilterStatus').value;
        const priorityF = document.getElementById('blFilterPriority').value;
        let filtered = items;
        if (typeF) filtered = filtered.filter(i => i.wricef_type === typeF);
        if (statusF) filtered = filtered.filter(i => i.status === statusF);
        if (priorityF) filtered = filtered.filter(i => i.priority === priorityF);
        document.getElementById('backlogTableBody').innerHTML = _renderTableRows(filtered);
    }

    // ── Sprints Tab ──────────────────────────────────────────────────────
    function renderSprints() {
        const c = document.getElementById('backlogContent');

        c.innerHTML = `
            <div style="margin-top:12px;display:flex;justify-content:flex-end">
                <button class="btn btn-primary" onclick="BacklogView.showCreateSprintModal()">+ New Sprint</button>
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
                                <div>
                                    <button class="btn btn-secondary btn-sm" onclick="BacklogView.showEditSprintModal(${s.id})">Edit</button>
                                    <button class="btn btn-danger btn-sm" onclick="BacklogView.deleteSprint(${s.id})">Delete</button>
                                </div>
                            </div>
                            ${s.goal ? `<p style="margin:8px 0;color:var(--sap-text-secondary)">${escHtml(s.goal)}</p>` : ''}
                            <div class="sprint-metrics">
                                <span><strong>${sprintItems.length}</strong> items</span>
                                <span><strong>${totalPts}</strong> points</span>
                                <span><strong>${donePts}</strong> done</span>
                                ${s.capacity_points ? `<span>Capacity: <strong>${s.capacity_points}</strong></span>` : ''}
                                ${s.velocity != null ? `<span>Velocity: <strong>${s.velocity}</strong></span>` : ''}
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
                <div class="card-header"><h3>📦 Unassigned Backlog</h3></div>
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
            <div style="margin-top:12px;display:flex;justify-content:flex-end">
                <button class="btn btn-primary" onclick="BacklogView.showCreateConfigModal()">+ New Config Item</button>
            </div>
            ${configItems.length === 0 ? `
                <div class="empty-state" style="margin-top:20px">
                    <div class="empty-state__icon">⚙️</div>
                    <div class="empty-state__title">No config items yet</div>
                    <p>Create configuration items to track SAP customizing changes.</p>
                </div>` : `
            <div class="card" style="margin-top:12px">
                <table class="data-table">
                    <thead>
                        <tr><th>Code</th><th>Title</th><th>Module</th><th>Config Key</th><th>Status</th><th>Priority</th><th>Assigned</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        ${configItems.map(ci => `
                            <tr onclick="BacklogView.openConfigDetail(${ci.id})" style="cursor:pointer">
                                <td><strong>${escHtml(ci.code || '—')}</strong></td>
                                <td>${escHtml(ci.title)}</td>
                                <td>${escHtml(ci.module || '—')}</td>
                                <td>${escHtml(ci.config_key || '—')}</td>
                                <td><span class="badge badge-${ci.status}">${STATUS_LABELS[ci.status] || ci.status}</span></td>
                                <td><span class="badge badge-${ci.priority}">${ci.priority}</span></td>
                                <td>${escHtml(ci.assigned_to || '—')}</td>
                                <td>
                                    <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();BacklogView.showEditConfigModal(${ci.id})">Edit</button>
                                    <button class="btn btn-danger btn-sm" onclick="event.stopPropagation();BacklogView.deleteConfigItem(${ci.id})">Delete</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`}`;
    }

    function showCreateConfigModal() { _showConfigForm(null); }

    async function showEditConfigModal(id) {
        try {
            const ci = await API.get(`/config-items/${id}`);
            _showConfigForm(ci);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function _showConfigForm(item) {
        const isEdit = !!item;
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
                <div class="form-group"><label>Assigned To</label><input id="ciAssigned" class="form-input" value="${escHtml(item?.assigned_to || '')}"></div>
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
            assigned_to: document.getElementById('ciAssigned').value.trim(),
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
            currentItem = await API.get(`/backlog/${id}`);
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
        document.getElementById('detailTabContent').innerHTML = `
            <div class="card" style="margin-top:12px">
                <h3>📘 Functional Specification</h3>
                ${fs ? `
                    <dl class="detail-list">
                        <dt>Title</dt><dd>${escHtml(fs.title)}</dd>
                        <dt>Status</dt><dd><span class="badge badge-${fs.status}">${fs.status}</span></dd>
                        <dt>Version</dt><dd>${fs.version || '—'}</dd>
                        <dt>Prepared By</dt><dd>${escHtml(fs.prepared_by || '—')}</dd>
                        <dt>Approved By</dt><dd>${escHtml(fs.approved_by || '—')}</dd>
                    </dl>
                    ${fs.content ? `<div style="margin-top:12px;white-space:pre-wrap;background:var(--sap-bg-secondary);padding:12px;border-radius:8px">${escHtml(fs.content)}</div>` : ''}
                ` : '<p style="color:var(--sap-text-secondary)">No functional specification linked yet.</p>'}
            </div>
            <div class="card" style="margin-top:16px">
                <h3>📙 Technical Specification</h3>
                ${ts ? `
                    <dl class="detail-list">
                        <dt>Title</dt><dd>${escHtml(ts.title)}</dd>
                        <dt>Status</dt><dd><span class="badge badge-${ts.status}">${ts.status}</span></dd>
                        <dt>Version</dt><dd>${ts.version || '—'}</dd>
                        <dt>Prepared By</dt><dd>${escHtml(ts.prepared_by || '—')}</dd>
                    </dl>
                    ${ts.content ? `<div style="margin-top:12px;white-space:pre-wrap;background:var(--sap-bg-secondary);padding:12px;border-radius:8px">${escHtml(ts.content)}</div>` : ''}
                ` : '<p style="color:var(--sap-text-secondary)">No technical specification linked yet.</p>'}
            </div>
        `;
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
            const stats = await API.get(`/programs/${programId}/backlog/stats`);
            const typeRows = Object.entries(stats.by_wricef_type).map(([k, v]) => {
                const w = WRICEF[k] || WRICEF.enhancement;
                return `<tr><td>${w.icon} ${w.label}</td><td>${v}</td></tr>`;
            }).join('');
            const statusRows = Object.entries(stats.by_status).map(([k, v]) =>
                `<tr><td><span class="badge badge-${k}">${STATUS_LABELS[k] || k}</span></td><td>${v}</td></tr>`
            ).join('');

            App.openModal(`
                <h2>Backlog Statistics</h2>
                <div class="detail-grid" style="margin-top:16px">
                    <div>
                        <h4>By WRICEF Type</h4>
                        <table class="data-table"><thead><tr><th>Type</th><th>Count</th></tr></thead>
                        <tbody>${typeRows || '<tr><td colspan="2">No data</td></tr>'}</tbody></table>
                    </div>
                    <div>
                        <h4>By Status</h4>
                        <table class="data-table"><thead><tr><th>Status</th><th>Count</th></tr></thead>
                        <tbody>${statusRows || '<tr><td colspan="2">No data</td></tr>'}</tbody></table>
                    </div>
                </div>
                <div style="margin-top:16px">
                    <p><strong>Total Items:</strong> ${stats.total_items}</p>
                    <p><strong>Total Story Points:</strong> ${stats.total_story_points}</p>
                    <p><strong>Estimated Hours:</strong> ${stats.total_estimated_hours}</p>
                    <p><strong>Actual Hours:</strong> ${stats.total_actual_hours}</p>
                </div>
                <div style="text-align:right;margin-top:20px">
                    <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
                </div>
            `);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Create Item Modal ────────────────────────────────────────────────
    function showCreateModal() {
        _showItemForm(null);
    }

    function showEditModal() {
        if (!currentItem) return;
        _showItemForm(currentItem);
    }

    function _showItemForm(item) {
        const isEdit = !!item;
        const title = isEdit ? 'Edit Backlog Item' : 'New Backlog Item';

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
                    <div class="form-group"><label>Assigned To</label><input id="biAssigned" class="form-input" value="${escHtml(item?.assigned_to || '')}"></div>
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
            assigned_to: document.getElementById('biAssigned').value.trim(),
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
    function showMoveModal() {
        if (!currentItem) return;
        App.openModal(`
            <h2>Move Item</h2>
            <div class="form-group"><label>Status</label>
                <select id="moveStatus" class="form-input">
                    ${Object.entries(STATUS_LABELS).map(([k, v]) =>
                        `<option value="${k}" ${currentItem.status === k ? 'selected' : ''}>${v}</option>`
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
            await API.patch(`/backlog/${currentItem.id}/move`, {
                status: document.getElementById('moveStatus').value,
                sprint_id: parseInt(document.getElementById('moveSprint').value) || null,
            });
            App.toast('Item moved', 'success');
            App.closeModal();
            await render();
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

    // Public API
    return {
        render, switchTab, applyListFilter,
        showCreateModal, showEditModal, saveItem,
        openDetail, deleteItem, switchDetailTab,
        showMoveModal, doMove,
        showStats,
        showCreateSprintModal, showEditSprintModal, saveSprint, deleteSprint,
        showCreateConfigModal, showEditConfigModal, saveConfigItem, deleteConfigItem,
        openConfigDetail,
    };
})();
