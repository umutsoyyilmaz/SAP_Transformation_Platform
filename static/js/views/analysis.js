/**
 * SAP Transformation Platform — Analysis Hub
 *
 * 4-tab view for managing workshops, process tree, scope matrix, and KPI dashboard.
 *
 * Tab 1: Workshop Planner   — Cross-scenario workshop calendar / kanban / list
 * Tab 2: Process Tree        — L1→L2→L3 hierarchy with scope items
 * Tab 3: Scope Matrix        — Flat fit/gap grid with inline analysis
 * Tab 4: Analysis Dashboard  — KPI charts & alerts
 */

const AnalysisView = (() => {
    let programId = null;
    let activeTab = 'workshops';
    let workshops = [];
    let scenarios = [];
    let scopeMatrix = [];
    let dashboardData = null;
    let processTree = [];

    // Selected scenario for process tree
    let selectedScenarioId = null;

    // View mode for workshops tab
    let wsViewMode = 'list'; // 'list' | 'kanban' | 'calendar'
    let wsFilterStatus = '';
    let wsFilterType = '';
    let wsFilterScenario = '';

    const SESSION_TYPES = {
        fit_gap_workshop:      { label: 'Fit-Gap Workshop', icon: '🔍', color: '#0070f2' },
        requirement_gathering: { label: 'Requirement Gathering', icon: '📋', color: '#1a9898' },
        process_mapping:       { label: 'Process Mapping', icon: '🗺️', color: '#925ace' },
        review:                { label: 'Review', icon: '📝', color: '#d04a02' },
        design_workshop:       { label: 'Design Workshop', icon: '🎨', color: '#e76500' },
        demo:                  { label: 'Demo', icon: '🖥️', color: '#188918' },
        sign_off:              { label: 'Sign-Off', icon: '✅', color: '#30914c' },
        training:              { label: 'Training', icon: '🎓', color: '#5b738b' },
    };

    const PROCESS_AREAS = {
        order_to_cash: 'Order to Cash (O2C)',
        procure_to_pay: 'Procure to Pay (P2P)',
        record_to_report: 'Record to Report (R2R)',
        plan_to_produce: 'Plan to Produce (P2P)',
        hire_to_retire: 'Hire to Retire (H2R)',
        warehouse_mgmt: 'Warehouse Management',
        project_mgmt: 'Project Management',
        plant_maintenance: 'Plant Maintenance',
        quality_mgmt: 'Quality Management',
        other: 'Other',
    };

    // ── Main Render ──────────────────────────────────────────────────────
    async function render() {
        const prog = App.getActiveProgram();
        if (!prog) return;
        programId = prog.id;

        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <h1>🔬 Analysis Hub</h1>
            </div>
            <div class="ah-tabs">
                <button class="ah-tab ${activeTab === 'workshops' ? 'ah-tab--active' : ''}" onclick="AnalysisView.switchTab('workshops')">📅 Workshop Planner</button>
                <button class="ah-tab ${activeTab === 'process-tree' ? 'ah-tab--active' : ''}" onclick="AnalysisView.switchTab('process-tree')">🌳 Process Tree</button>
                <button class="ah-tab ${activeTab === 'scope-matrix' ? 'ah-tab--active' : ''}" onclick="AnalysisView.switchTab('scope-matrix')">📊 Scope Matrix</button>
                <button class="ah-tab ${activeTab === 'dashboard' ? 'ah-tab--active' : ''}" onclick="AnalysisView.switchTab('dashboard')">📈 Dashboard</button>
            </div>
            <div id="ahTabContent" class="ah-tab-content"></div>
        `;

        // Load scenarios (needed by most tabs)
        try { scenarios = await API.get(`/programs/${programId}/scenarios`); } catch(e) { scenarios = []; }

        await renderActiveTab();
    }

    function switchTab(tab) {
        activeTab = tab;
        document.querySelectorAll('.ah-tab').forEach(el => {
            el.classList.toggle('ah-tab--active', el.textContent.toLowerCase().includes(tab.split('-')[0]));
        });
        // Simpler approach: re-highlight
        document.querySelectorAll('.ah-tab').forEach(el => el.classList.remove('ah-tab--active'));
        const tabMap = { 'workshops': 0, 'process-tree': 1, 'scope-matrix': 2, 'dashboard': 3 };
        document.querySelectorAll('.ah-tab')[tabMap[tab]]?.classList.add('ah-tab--active');
        renderActiveTab();
    }

    async function renderActiveTab() {
        switch (activeTab) {
            case 'workshops': return await renderWorkshopsTab();
            case 'process-tree': return await renderProcessTreeTab();
            case 'scope-matrix': return await renderScopeMatrixTab();
            case 'dashboard': return await renderDashboardTab();
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  TAB 1: Workshop Planner
    // ═══════════════════════════════════════════════════════════════════════

    async function renderWorkshopsTab() {
        const c = document.getElementById('ahTabContent');
        c.innerHTML = '<div class="spinner"></div>';

        try { workshops = await API.get(`/programs/${programId}/workshops`); } catch(e) { workshops = []; }

        const scenarioOpts = scenarios.map(s => `<option value="${s.id}" ${wsFilterScenario == s.id ? 'selected' : ''}>${esc(s.name)}</option>`).join('');

        c.innerHTML = `
            <div class="ah-toolbar">
                <div class="ah-toolbar__left">
                    <button class="btn btn-sm ${wsViewMode === 'list' ? 'btn-primary' : 'btn-secondary'}" onclick="AnalysisView.setWsView('list')">☰ List</button>
                    <button class="btn btn-sm ${wsViewMode === 'kanban' ? 'btn-primary' : 'btn-secondary'}" onclick="AnalysisView.setWsView('kanban')">▦ Kanban</button>
                    <button class="btn btn-sm ${wsViewMode === 'calendar' ? 'btn-primary' : 'btn-secondary'}" onclick="AnalysisView.setWsView('calendar')">📅 Calendar</button>
                </div>
                <div class="ah-toolbar__right">
                    <select class="form-input form-input--sm" onchange="AnalysisView.wsFilterByScenario(this.value)">
                        <option value="">All Scenarios</option>
                        ${scenarioOpts}
                    </select>
                    <select class="form-input form-input--sm" onchange="AnalysisView.wsFilterByType(this.value)">
                        <option value="">All Types</option>
                        ${Object.entries(SESSION_TYPES).map(([k,v]) => `<option value="${k}" ${wsFilterType === k ? 'selected' : ''}>${v.icon} ${v.label}</option>`).join('')}
                    </select>
                    <select class="form-input form-input--sm" onchange="AnalysisView.wsFilterByStatus(this.value)">
                        <option value="">All Status</option>
                        <option value="planned" ${wsFilterStatus === 'planned' ? 'selected' : ''}>Planned</option>
                        <option value="in_progress" ${wsFilterStatus === 'in_progress' ? 'selected' : ''}>In Progress</option>
                        <option value="completed" ${wsFilterStatus === 'completed' ? 'selected' : ''}>Completed</option>
                        <option value="cancelled" ${wsFilterStatus === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                    </select>
                </div>
            </div>
            <div class="ah-ws-summary">
                <span class="badge badge-info">${workshops.length} workshops</span>
                <span class="badge badge-planned">${workshops.filter(w => w.status === 'planned').length} planned</span>
                <span class="badge badge-in_progress">${workshops.filter(w => w.status === 'in_progress').length} in progress</span>
                <span class="badge badge-completed">${workshops.filter(w => w.status === 'completed').length} completed</span>
            </div>
            <div id="wsViewContainer"></div>
        `;

        renderWsView();
    }

    function getFilteredWorkshops() {
        let filtered = [...workshops];
        if (wsFilterStatus) filtered = filtered.filter(w => w.status === wsFilterStatus);
        if (wsFilterType) filtered = filtered.filter(w => w.session_type === wsFilterType);
        if (wsFilterScenario) filtered = filtered.filter(w => w.scenario_id == wsFilterScenario);
        return filtered;
    }

    function renderWsView() {
        const filtered = getFilteredWorkshops();
        const container = document.getElementById('wsViewContainer');
        if (!container) return;

        switch (wsViewMode) {
            case 'list': return renderWsList(container, filtered);
            case 'kanban': return renderWsKanban(container, filtered);
            case 'calendar': return renderWsCalendar(container, filtered);
        }
    }

    function renderWsList(c, items) {
        if (items.length === 0) {
            c.innerHTML = '<div class="empty-state"><div class="empty-state__icon">📅</div><div class="empty-state__title">No workshops found</div></div>';
            return;
        }
        c.innerHTML = `
            <table class="data-table">
                <thead><tr>
                    <th>Workshop</th><th>Scenario</th><th>Type</th><th>Status</th>
                    <th>Date</th><th>Facilitator</th><th>Fit/Gap/Partial</th><th>Actions</th>
                </tr></thead>
                <tbody>
                    ${items.map(w => {
                        const t = SESSION_TYPES[w.session_type] || { label: w.session_type, icon: '📄', color: '#5b738b' };
                        const d = w.session_date ? new Date(w.session_date).toLocaleDateString('tr-TR') : '—';
                        return `<tr>
                            <td><strong>${esc(w.title)}</strong></td>
                            <td><span class="badge badge-info">${esc(w.scenario_name || '')}</span></td>
                            <td><span class="badge" style="background:${t.color}22;color:${t.color}">${t.icon} ${t.label}</span></td>
                            <td><span class="badge badge-${w.status}">${fmtStatus(w.status)}</span></td>
                            <td>${d}</td>
                            <td>${esc(w.facilitator || '—')}</td>
                            <td>
                                ${(w.fit_count || w.gap_count || w.partial_fit_count) ?
                                    `<span class="count-fit">✓${w.fit_count||0}</span>
                                     <span class="count-gap">✗${w.gap_count||0}</span>
                                     <span class="count-partial">◐${w.partial_fit_count||0}</span>` : '—'}
                            </td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="AnalysisView.viewWorkshop(${w.id}, ${w.scenario_id})">View</button>
                            </td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>`;
    }

    function renderWsKanban(c, items) {
        const cols = ['planned', 'in_progress', 'completed', 'cancelled'];
        c.innerHTML = `
            <div class="ah-kanban">
                ${cols.map(status => {
                    const cards = items.filter(w => w.status === status);
                    return `
                    <div class="ah-kanban__col">
                        <div class="ah-kanban__col-header">
                            <span>${fmtStatus(status)}</span>
                            <span class="badge">${cards.length}</span>
                        </div>
                        <div class="ah-kanban__cards">
                            ${cards.length === 0 ? '<div class="ah-kanban__empty">No items</div>' :
                            cards.map(w => {
                                const t = SESSION_TYPES[w.session_type] || { label: w.session_type, icon: '📄', color: '#5b738b' };
                                const d = w.session_date ? new Date(w.session_date).toLocaleDateString('tr-TR') : '';
                                return `
                                <div class="ah-kanban__card" onclick="AnalysisView.viewWorkshop(${w.id}, ${w.scenario_id})">
                                    <div class="ah-kanban__card-type" style="border-left:4px solid ${t.color}">
                                        <strong>${esc(w.title)}</strong>
                                    </div>
                                    <div class="ah-kanban__card-meta">
                                        <span class="badge" style="background:${t.color}22;color:${t.color};font-size:10px">${t.icon} ${t.label}</span>
                                        <span style="font-size:11px;color:var(--sap-text-secondary)">${esc(w.scenario_name || '')}</span>
                                    </div>
                                    ${d ? `<div style="font-size:11px;color:var(--sap-text-secondary)">📅 ${d}</div>` : ''}
                                    ${(w.fit_count || w.gap_count || w.partial_fit_count) ? `
                                    <div class="workshop-card__counts" style="margin-top:4px;font-size:11px">
                                        <span class="count-fit">✓${w.fit_count||0}</span>
                                        <span class="count-gap">✗${w.gap_count||0}</span>
                                        <span class="count-partial">◐${w.partial_fit_count||0}</span>
                                    </div>` : ''}
                                </div>`;
                            }).join('')}
                        </div>
                    </div>`;
                }).join('')}
            </div>`;
    }

    function renderWsCalendar(c, items) {
        // Simple monthly calendar view
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const firstDay = new Date(year, month, 1).getDay(); // 0=Sun
        const startOffset = firstDay === 0 ? 6 : firstDay - 1; // Mon=0

        const monthName = new Date(year, month).toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' });

        // Map workshops to days
        const dayMap = {};
        items.forEach(w => {
            if (!w.session_date) return;
            const d = new Date(w.session_date);
            if (d.getFullYear() === year && d.getMonth() === month) {
                const day = d.getDate();
                if (!dayMap[day]) dayMap[day] = [];
                dayMap[day].push(w);
            }
        });

        let cells = '';
        // Empty cells for offset
        for (let i = 0; i < startOffset; i++) cells += '<div class="ah-cal__cell ah-cal__cell--empty"></div>';
        for (let d = 1; d <= daysInMonth; d++) {
            const ws = dayMap[d] || [];
            const isToday = d === now.getDate() && month === now.getMonth() && year === now.getFullYear();
            cells += `
                <div class="ah-cal__cell ${isToday ? 'ah-cal__cell--today' : ''}">
                    <span class="ah-cal__day">${d}</span>
                    ${ws.map(w => {
                        const t = SESSION_TYPES[w.session_type] || { icon: '📄', color: '#5b738b', label: '' };
                        return `<div class="ah-cal__event" style="background:${t.color}22;color:${t.color};border-left:3px solid ${t.color}" onclick="AnalysisView.viewWorkshop(${w.id}, ${w.scenario_id})" title="${esc(w.title)}">${t.icon} ${esc(w.title.length > 15 ? w.title.slice(0,15) + '…' : w.title)}</div>`;
                    }).join('')}
                </div>`;
        }

        const noDateWs = items.filter(w => !w.session_date);

        c.innerHTML = `
            <div class="ah-cal">
                <div class="ah-cal__header">
                    <h3>${monthName}</h3>
                </div>
                <div class="ah-cal__grid">
                    <div class="ah-cal__dow">Pzt</div><div class="ah-cal__dow">Sal</div>
                    <div class="ah-cal__dow">Çar</div><div class="ah-cal__dow">Per</div>
                    <div class="ah-cal__dow">Cum</div><div class="ah-cal__dow">Cmt</div>
                    <div class="ah-cal__dow">Paz</div>
                    ${cells}
                </div>
            </div>
            ${noDateWs.length > 0 ? `
            <div class="card" style="margin-top:16px">
                <div class="card-header"><h3>Unscheduled Workshops (${noDateWs.length})</h3></div>
                <div class="ah-unscheduled">
                    ${noDateWs.map(w => {
                        const t = SESSION_TYPES[w.session_type] || { icon: '📄', color: '#5b738b', label: w.session_type };
                        return `<div class="badge" style="margin:4px;cursor:pointer;background:${t.color}22;color:${t.color}" onclick="AnalysisView.viewWorkshop(${w.id}, ${w.scenario_id})">${t.icon} ${esc(w.title)} <span style="opacity:.6">(${esc(w.scenario_name||'')})</span></div>`;
                    }).join('')}
                </div>
            </div>` : ''}
        `;
    }

    function setWsView(mode) { wsViewMode = mode; renderWorkshopsTab(); }
    function wsFilterByStatus(v) { wsFilterStatus = v; renderWsView(); }
    function wsFilterByType(v) { wsFilterType = v; renderWsView(); }
    function wsFilterByScenario(v) { wsFilterScenario = v; renderWsView(); }

    function viewWorkshop(wid, scenarioId) {
        // Navigate to scenario view and open workshop detail
        if (typeof ScenarioView !== 'undefined') {
            ScenarioView.openWorkshop(wid);
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    //  TAB 2: Process Tree
    // ═══════════════════════════════════════════════════════════════════════

    async function renderProcessTreeTab() {
        const c = document.getElementById('ahTabContent');

        if (scenarios.length === 0) {
            c.innerHTML = '<div class="empty-state"><div class="empty-state__icon">🌳</div><div class="empty-state__title">No scenarios</div><p>Create scenarios first to build process trees.</p></div>';
            return;
        }

        if (!selectedScenarioId) selectedScenarioId = scenarios[0].id;

        c.innerHTML = `
            <div class="ah-toolbar">
                <div class="ah-toolbar__left">
                    <label style="font-weight:600;margin-right:8px">Scenario:</label>
                    <select class="form-input form-input--sm" id="ptScenarioSelect" onchange="AnalysisView.selectTreeScenario(this.value)">
                        ${scenarios.map(s => `<option value="${s.id}" ${selectedScenarioId == s.id ? 'selected' : ''}>${esc(s.name)} ${s.sap_module ? '('+s.sap_module+')' : ''}</option>`).join('')}
                    </select>
                </div>
                <div class="ah-toolbar__right">
                    <button class="btn btn-primary btn-sm" onclick="AnalysisView.showAddL2ProcessModal()">+ Add Process</button>
                </div>
            </div>
            <div class="ah-tree-container">
                <div class="ah-tree" id="processTreePanel">
                    <div class="spinner"></div>
                </div>
                <div class="ah-tree-detail" id="processDetailPanel">
                    <div class="empty-state" style="padding:40px">
                        <div class="empty-state__icon">👈</div>
                        <div class="empty-state__title">Select a process</div>
                        <p>Click a process node to see its scope items.</p>
                    </div>
                </div>
            </div>`;

        await loadProcessTree();
    }

    async function loadProcessTree() {
        try {
            processTree = await API.get(`/scenarios/${selectedScenarioId}/processes?tree=true`);
        } catch(e) { processTree = []; }
        renderTree();
    }

    function renderTree() {
        const panel = document.getElementById('processTreePanel');
        if (!panel) return;

        if (processTree.length === 0) {
            panel.innerHTML = `
                <div class="empty-state" style="padding:30px">
                    <div class="empty-state__icon">🌳</div>
                    <div class="empty-state__title">No processes yet</div>
                    <p>Add L1 processes to start building the hierarchy.</p>
                    <br>
                    <button class="btn btn-primary btn-sm" onclick="AnalysisView.showAddProcessModal()">+ Add L1 Process</button>
                </div>`;
            return;
        }

        panel.innerHTML = renderTreeNodes(processTree, 0);
    }

    function renderTreeNodes(nodes, depth) {
        return nodes.map(n => {
            const children = n.children || [];
            const hasChildren = children.length > 0;
            const levelBadgeColor = n.level === 'L1' ? '#0070f2' : n.level === 'L2' ? '#1a9898' : '#925ace';
            const indent = depth * 20;

            return `
                <div class="ah-tree-node" style="padding-left:${indent}px">
                    <div class="ah-tree-node__row" onclick="AnalysisView.selectProcess(${n.id})">
                        <span class="ah-tree-node__toggle ${hasChildren ? '' : 'ah-tree-node__toggle--leaf'}"
                              onclick="event.stopPropagation(); AnalysisView.toggleTreeNode(this)">
                            ${hasChildren ? '▶' : '•'}
                        </span>
                        <span class="badge" style="background:${levelBadgeColor}22;color:${levelBadgeColor};font-size:10px;margin-right:6px">${n.level}</span>
                        <span class="ah-tree-node__name">${esc(n.name)}</span>
                        ${n.process_id_code ? `<span style="color:var(--sap-text-secondary);font-size:11px;margin-left:6px">${esc(n.process_id_code)}</span>` : ''}
                        <span class="ah-tree-node__actions">
                            <button class="btn btn-secondary btn-sm" style="font-size:10px;padding:2px 6px" onclick="event.stopPropagation(); AnalysisView.showAddProcessModal(${n.id}, '${n.level === 'L1' ? 'L2' : 'L3'}')">+ Child</button>
                            <button class="btn btn-danger btn-sm" style="font-size:10px;padding:2px 6px" onclick="event.stopPropagation(); AnalysisView.deleteProcess(${n.id})">✗</button>
                        </span>
                    </div>
                    ${hasChildren ? `<div class="ah-tree-node__children">${renderTreeNodes(children, depth + 1)}</div>` : ''}
                </div>`;
        }).join('');
    }

    function toggleTreeNode(el) {
        const node = el.closest('.ah-tree-node');
        const children = node.querySelector('.ah-tree-node__children');
        if (!children) return;
        const isOpen = children.style.display !== 'none';
        children.style.display = isOpen ? 'none' : 'block';
        el.textContent = isOpen ? '▶' : '▼';
    }

    async function selectProcess(pid) {
        const panel = document.getElementById('processDetailPanel');
        panel.innerHTML = '<div class="spinner"></div>';

        try {
            const proc = await API.get(`/processes/${pid}?include_children=false`);
            const items = await API.get(`/processes/${pid}/scope-items?include_analysis=true`);

            panel.innerHTML = `
                <div class="ah-scope-panel">
                    <div class="ah-scope-panel__header">
                        <h3>${esc(proc.name)}</h3>
                        <span class="badge" style="background:#0070f222;color:#0070f2">${proc.level}</span>
                        ${proc.module ? `<span class="badge badge-info">${esc(proc.module)}</span>` : ''}
                    </div>
                    ${proc.description ? `<p style="color:var(--sap-text-secondary);margin-bottom:12px">${esc(proc.description)}</p>` : ''}
                    <div class="ah-scope-panel__actions">
                        <button class="btn btn-primary btn-sm" onclick="AnalysisView.showAddRequirementModal(${pid})">+ Requirement</button>
                    </div>
                    <div id="scopeItemsList">
                        ${items.length === 0 ? '<p style="color:var(--sap-text-secondary);padding:12px">No scope items yet.</p>' :
                        `<table class="data-table">
                            <thead><tr><th>Code</th><th>Name</th><th>SAP Ref</th><th>Fit/Gap</th><th>Status</th><th>Priority</th></tr></thead>
                            <tbody>
                                ${items.map(si => `
                                <tr class="ah-clickable-row" onclick="AnalysisView.showScopeItemDetail(${si.id})" title="Click to view details">
                                    <td><strong>${esc(si.code || '—')}</strong></td>
                                    <td>${esc(si.name)}</td>
                                    <td>${esc(si.sap_reference || '—')}</td>
                                    <td>${si.latest_fit_gap ? `<span class="badge badge-${si.latest_fit_gap}">${fmtFitGap(si.latest_fit_gap)}</span>` : '<span style="color:var(--sap-text-secondary)">—</span>'}</td>
                                    <td><span class="badge badge-${si.status}">${fmtStatus(si.status)}</span></td>
                                    <td><span class="badge badge-priority-${si.priority}">${si.priority}</span></td>
                                </tr>`).join('')}
                            </tbody>
                        </table>`}
                    </div>
                </div>`;
        } catch(e) {
            panel.innerHTML = `<div class="empty-state"><p>Error loading process: ${e.message}</p></div>`;
        }
    }

    function selectTreeScenario(sid) {
        selectedScenarioId = sid;
        loadProcessTree();
        // Reset detail panel
        const dp = document.getElementById('processDetailPanel');
        if (dp) dp.innerHTML = '<div class="empty-state" style="padding:40px"><div class="empty-state__icon">👈</div><div class="empty-state__title">Select a process</div></div>';
    }

    // ── Scope Item Detail (popup-like inline)
    async function showScopeItemDetail(siid) {
        try {
            const item = await API.get(`/scope-items/${siid}`);
            const analyses = item.analyses || [];
            App.openModal(`
                <div class="modal-header"><h2>Scope Item: ${esc(item.code || '')} ${esc(item.name)}</h2></div>
                <div class="modal-body">
                    <dl class="detail-list">
                        <dt>SAP Reference</dt><dd>${esc(item.sap_reference || '—')}</dd>
                        <dt>Status</dt><dd><span class="badge badge-${item.status}">${fmtStatus(item.status)}</span></dd>
                        <dt>Priority</dt><dd><span class="badge badge-priority-${item.priority}">${item.priority}</span></dd>
                        <dt>Module</dt><dd>${esc(item.module || '—')}</dd>
                        <dt>Linked Requirement</dt><dd>${item.requirement ? `<a href="#" onclick="App.navigate('requirements');setTimeout(()=>RequirementView.openDetail(${item.requirement.id}),300);App.closeModal();return false">${esc(item.requirement.code)} — ${esc(item.requirement.title)}</a>` : '<em>Not linked</em>'}</dd>
                    </dl>
                    ${item.description ? `<p>${esc(item.description)}</p>` : ''}
                    ${item.notes ? `<p style="color:var(--sap-text-secondary)">${esc(item.notes)}</p>` : ''}
                    <hr>
                    <h3>Analyses (${analyses.length})</h3>
                    ${analyses.length === 0 ? '<p style="color:var(--sap-text-secondary)">No analyses recorded.</p>' :
                    `<table class="data-table">
                        <thead><tr><th>Name</th><th>Type</th><th>Result</th><th>Status</th><th>Date</th></tr></thead>
                        <tbody>
                            ${analyses.map(a => `
                            <tr>
                                <td>${esc(a.name)}</td>
                                <td>${a.analysis_type}</td>
                                <td>${a.fit_gap_result ? `<span class="badge badge-${a.fit_gap_result}">${a.fit_gap_result}</span>` : '—'}</td>
                                <td><span class="badge badge-${a.status}">${fmtStatus(a.status)}</span></td>
                                <td>${a.date || '—'}</td>
                            </tr>`).join('')}
                        </tbody>
                    </table>`}
                    <div id="aiAnalystPanel" class="ai-assistant-panel" style="margin-top:12px"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-danger btn-sm" onclick="AnalysisView.deleteScopeItem(${item.id}, ${item.process_id})">Delete</button>
                    <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
                </div>
            `);

            // Load linked requirements for AI analysis button
            _loadAIAnalystPanel(item);
        } catch(e) { App.toast(e.message, 'error'); }
    }

    /**
     * Task 8.7 — Requirement Analyst → Scope integration.
     * Shows AI Classify button for linked requirements and displays results.
     */
    async function _loadAIAnalystPanel(scopeItem) {
        const panel = document.getElementById('aiAnalystPanel');
        if (!panel) return;

        // Find linked requirements via traceability or analyses
        let reqIds = [];
        try {
            const traces = await API.get(`/traceability/linked-items/scope_item/${scopeItem.id}`);
            reqIds = (traces.items || [])
                .filter(t => t.entity_type === 'requirement')
                .map(t => t.entity_id);
        } catch(e) { /* traceability may return empty */ }

        if (reqIds.length === 0) {
            // Try to find requirements linked to this scope item's process
            try {
                const reqs = await API.get(`/programs/${programId}/requirements?per_page=5`);
                reqIds = (reqs.items || reqs || []).slice(0, 3).map(r => r.id);
            } catch(e) { /* ignore */ }
        }

        if (reqIds.length === 0) {
            panel.innerHTML = `
                <div class="ai-assistant-hint">
                    <span>🤖</span> <em>No linked requirements found for AI analysis.</em>
                </div>`;
            return;
        }

        panel.innerHTML = `
            <div class="ai-assistant-section">
                <div class="ai-assistant-header">
                    <span>🤖 AI Requirement Analyst</span>
                    <button class="btn btn-sm btn-ai" id="btnAIClassify"
                        onclick="AnalysisView.runAIClassify([${reqIds.join(',')}])">
                        🎯 Classify Fit/Gap (${reqIds.length} req)
                    </button>
                </div>
                <div id="aiClassifyResults"></div>
            </div>`;
    }

    async function runAIClassify(reqIds) {
        const btn = document.getElementById('btnAIClassify');
        const results = document.getElementById('aiClassifyResults');
        if (!btn || !results) return;

        btn.disabled = true;
        btn.textContent = '⏳ Analyzing...';
        results.innerHTML = '<div class="spinner" style="margin:8px auto"></div>';

        try {
            const data = await API.post('/ai/analyst/requirement/batch', {
                requirement_ids: reqIds,
                create_suggestion: true,
            });

            results.innerHTML = (data.results || []).map(r => {
                if (r.error) {
                    return `<div class="ai-result-item ai-result--error">
                        <strong>Req #${r.requirement_id}</strong>: ${esc(r.error)}
                    </div>`;
                }
                const confPct = Math.round((r.confidence || 0) * 100);
                const confClass = confPct >= 80 ? 'high' : confPct >= 50 ? 'medium' : 'low';
                return `<div class="ai-result-item">
                    <div class="ai-result-header">
                        <span class="badge badge-${r.classification || 'unknown'}">${r.classification || '?'}</span>
                        <span class="badge badge-confidence-${confClass}">${confPct}%</span>
                        ${r.suggestion_id ? '<span class="badge badge-pending">📋 Suggestion created</span>' : ''}
                    </div>
                    <p class="ai-result-reasoning">${esc(r.reasoning || '')}</p>
                    ${r.sap_solution ? `<p class="ai-result-detail"><strong>SAP Solution:</strong> ${esc(r.sap_solution)}</p>` : ''}
                    ${(r.sap_transactions || []).length ? `<p class="ai-result-detail"><strong>Transactions:</strong> ${r.sap_transactions.map(t => esc(t)).join(', ')}</p>` : ''}
                    ${r.effort_estimate ? `<p class="ai-result-detail"><strong>Effort:</strong> ${esc(r.effort_estimate)}</p>` : ''}
                </div>`;
            }).join('') || '<p>No results.</p>';
        } catch(e) {
            results.innerHTML = `<div class="ai-result-item ai-result--error">⚠️ ${esc(e.message)}</div>`;
        } finally {
            btn.disabled = false;
            btn.textContent = `🎯 Classify Fit/Gap (${reqIds.length} req)`;
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    //  TAB 3: Scope Matrix
    // ═══════════════════════════════════════════════════════════════════════

    let smFilterModule = '';
    let smFilterStatus = '';
    let smFilterResult = '';

    async function renderScopeMatrixTab() {
        const c = document.getElementById('ahTabContent');
        c.innerHTML = '<div class="spinner"></div>';

        try { scopeMatrix = await API.get(`/programs/${programId}/scope-matrix`); } catch(e) { scopeMatrix = []; }

        // Gather unique values for filters
        const modules = [...new Set(scopeMatrix.map(r => r.sap_module).filter(Boolean))];

        // Calculate stats
        const total = scopeMatrix.length;
        const analyzed = scopeMatrix.filter(r => r.latest_analysis_status === 'completed').length;
        const fitCount = scopeMatrix.filter(r => r.latest_fit_gap === 'fit').length;
        const gapCount = scopeMatrix.filter(r => r.latest_fit_gap === 'gap').length;
        const partialCount = scopeMatrix.filter(r => r.latest_fit_gap === 'partial_fit').length;
        const pct = total > 0 ? Math.round(analyzed / total * 100) : 0;

        c.innerHTML = `
            <div class="ah-toolbar">
                <div class="ah-toolbar__left">
                    <select class="form-input form-input--sm" onchange="AnalysisView.smFilter('module', this.value)">
                        <option value="">All Modules</option>
                        ${modules.map(m => `<option value="${m}" ${smFilterModule === m ? 'selected' : ''}>${m}</option>`).join('')}
                    </select>
                    <select class="form-input form-input--sm" onchange="AnalysisView.smFilter('status', this.value)">
                        <option value="">All Status</option>
                        <option value="in_scope" ${smFilterStatus === 'in_scope' ? 'selected' : ''}>In Scope</option>
                        <option value="active" ${smFilterStatus === 'active' ? 'selected' : ''}>Active</option>
                        <option value="deferred" ${smFilterStatus === 'deferred' ? 'selected' : ''}>Deferred</option>
                        <option value="out_of_scope" ${smFilterStatus === 'out_of_scope' ? 'selected' : ''}>Out of Scope</option>
                    </select>
                    <select class="form-input form-input--sm" onchange="AnalysisView.smFilter('result', this.value)">
                        <option value="">All Results</option>
                        <option value="fit" ${smFilterResult === 'fit' ? 'selected' : ''}>Fit</option>
                        <option value="partial_fit" ${smFilterResult === 'partial_fit' ? 'selected' : ''}>Partial Fit</option>
                        <option value="gap" ${smFilterResult === 'gap' ? 'selected' : ''}>Gap</option>
                        <option value="none" ${smFilterResult === 'none' ? 'selected' : ''}>Not Analyzed</option>
                    </select>
                </div>
            </div>

            <div class="ah-progress-bar">
                <div class="ah-progress-bar__track">
                    <div class="ah-progress-bar__fill ah-progress-bar__fill--fit" style="width:${total > 0 ? fitCount/total*100 : 0}%"></div>
                    <div class="ah-progress-bar__fill ah-progress-bar__fill--partial" style="width:${total > 0 ? partialCount/total*100 : 0}%"></div>
                    <div class="ah-progress-bar__fill ah-progress-bar__fill--gap" style="width:${total > 0 ? gapCount/total*100 : 0}%"></div>
                </div>
                <div class="ah-progress-bar__labels">
                    <span>Analyzed: <strong>${analyzed}/${total}</strong> (${pct}%)</span>
                    <span class="count-fit">✓ Fit: ${fitCount}</span>
                    <span class="count-partial">◐ Partial: ${partialCount}</span>
                    <span class="count-gap">✗ Gap: ${gapCount}</span>
                </div>
            </div>

            <div id="scopeMatrixTable"></div>
        `;

        renderScopeMatrixTable();
    }

    function smFilter(type, val) {
        if (type === 'module') smFilterModule = val;
        if (type === 'status') smFilterStatus = val;
        if (type === 'result') smFilterResult = val;
        renderScopeMatrixTable();
    }

    function renderScopeMatrixTable() {
        let items = [...scopeMatrix];
        if (smFilterModule) items = items.filter(r => r.sap_module === smFilterModule);
        if (smFilterStatus) items = items.filter(r => r.status === smFilterStatus);
        if (smFilterResult) {
            if (smFilterResult === 'none') items = items.filter(r => !r.latest_fit_gap);
            else items = items.filter(r => r.latest_fit_gap === smFilterResult);
        }

        const container = document.getElementById('scopeMatrixTable');
        if (!container) return;

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state__icon">📊</div><div class="empty-state__title">No scope items found</div></div>';
            return;
        }

        container.innerHTML = `
            <table class="data-table">
                <thead><tr>
                    <th>Module</th><th>Scenario</th><th>Process</th><th>Code</th>
                    <th>Scope Item</th><th>Status</th><th>Fit/Gap Result</th>
                    <th>Analyses</th><th>Actions</th>
                </tr></thead>
                <tbody>
                    ${items.map(r => {
                        const resultBadge = r.latest_fit_gap
                            ? `<span class="badge badge-${r.latest_fit_gap}">${r.latest_fit_gap.replace('_', ' ')}</span>`
                            : '<span style="color:var(--sap-text-secondary)">—</span>';
                        return `
                        <tr>
                            <td>${esc(r.sap_module || '—')}</td>
                            <td>${esc(r.scenario_name)}</td>
                            <td><span class="badge" style="font-size:10px">${r.process_level}</span> ${esc(r.process_name)}</td>
                            <td><strong>${esc(r.code || '—')}</strong></td>
                            <td>${esc(r.name)}</td>
                            <td><span class="badge badge-${r.status}">${fmtStatus(r.status)}</span></td>
                            <td>${resultBadge}</td>
                            <td>
                                <span class="badge">${r.analysis_count}</span>
                            </td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="AnalysisView.showScopeItemDetail(${r.id})">Detail</button>
                                <select class="form-input form-input--sm" style="width:100px;display:inline-block"
                                    onchange="AnalysisView.quickFitGap(${r.id}, this.value)">
                                    <option value="">Quick F/G</option>
                                    <option value="fit">✓ Fit</option>
                                    <option value="partial_fit">◐ Partial</option>
                                    <option value="gap">✗ Gap</option>
                                </select>
                            </td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>`;
    }

    async function quickFitGap(scopeItemId, result) {
        if (!result) return;
        try {
            await API.post(`/scope-items/${scopeItemId}/analyses`, {
                name: `Quick ${result.replace('_', ' ')} assessment`,
                analysis_type: 'fit_gap',
                status: 'completed',
                fit_gap_result: result,
                date: new Date().toISOString().split('T')[0],
            });
            App.toast(`Marked as ${result.replace('_', ' ')}`, 'success');
            await renderScopeMatrixTab();
        } catch(e) { App.toast(e.message, 'error'); }
    }


    // ═══════════════════════════════════════════════════════════════════════
    //  TAB 4: Analysis Dashboard
    // ═══════════════════════════════════════════════════════════════════════

    async function renderDashboardTab() {
        const c = document.getElementById('ahTabContent');
        c.innerHTML = '<div class="spinner"></div>';

        try {
            dashboardData = await API.get(`/programs/${programId}/analysis-dashboard`);
        } catch(e) {
            c.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
            return;
        }

        const d = dashboardData;
        const coverage = d.coverage_pct || 0;

        c.innerHTML = `
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-card__value">${d.total_scope_items}</div>
                    <div class="kpi-card__label">Scope Items</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${d.analyzed_scope_items}</div>
                    <div class="kpi-card__label">Analyzed</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" style="color:${coverage >= 80 ? '#30914c' : coverage >= 50 ? '#e76500' : '#bb0000'}">${coverage}%</div>
                    <div class="kpi-card__label">Coverage</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${d.total_workshops}</div>
                    <div class="kpi-card__label">Workshops</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${d.total_analyses}</div>
                    <div class="kpi-card__label">Analysis Records</div>
                </div>
            </div>

            <div class="ah-alerts">
                ${d.pending_decisions > 0 ? `<div class="ah-alert ah-alert--warning">⚠️ <strong>${d.pending_decisions}</strong> analyses completed but no decision recorded</div>` : ''}
                ${d.gap_without_requirement > 0 ? `<div class="ah-alert ah-alert--danger">🔴 <strong>${d.gap_without_requirement}</strong> gap items without linked requirement</div>` : ''}
                ${(d.by_workshop_status?.planned || 0) > 0 ? `<div class="ah-alert ah-alert--info">📅 <strong>${d.by_workshop_status.planned}</strong> workshops still in planned status</div>` : ''}
            </div>

            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-header"><h2>Fit / Gap Distribution</h2></div>
                    <canvas id="ahFitGapChart" height="250"></canvas>
                </div>
                <div class="card">
                    <div class="card-header"><h2>Module Coverage</h2></div>
                    <canvas id="ahModuleChart" height="250"></canvas>
                </div>
            </div>
            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-header"><h2>Workshop Status</h2></div>
                    <canvas id="ahWsStatusChart" height="220"></canvas>
                </div>
                <div class="card">
                    <div class="card-header"><h2>Analysis by Type</h2></div>
                    <canvas id="ahAnalysisTypeChart" height="220"></canvas>
                </div>
            </div>
        `;

        // Render charts
        renderDashboardCharts(d);
    }

    function renderDashboardCharts(d) {
        if (typeof Chart === 'undefined') return;

        // Fit/Gap donut
        const fgLabels = Object.keys(d.by_fit_gap || {});
        const fgData = Object.values(d.by_fit_gap || {});
        const fgColors = fgLabels.map(l => l === 'fit' ? '#30914c' : l === 'partial_fit' ? '#e76500' : l === 'gap' ? '#bb0000' : '#a9b4be');

        if (fgLabels.length > 0) {
            new Chart(document.getElementById('ahFitGapChart'), {
                type: 'doughnut',
                data: { labels: fgLabels.map(l => l.replace('_', ' ')), datasets: [{ data: fgData, backgroundColor: fgColors }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
            });
        }

        // Module coverage bar
        const modules = Object.keys(d.by_module || {});
        const totalPerMod = modules.map(m => d.by_module[m] || 0);
        const analyzedPerMod = modules.map(m => d.by_module_analyzed?.[m] || 0);

        if (modules.length > 0) {
            new Chart(document.getElementById('ahModuleChart'), {
                type: 'bar',
                data: {
                    labels: modules,
                    datasets: [
                        { label: 'Analyzed', data: analyzedPerMod, backgroundColor: '#0070f2', borderRadius: 6 },
                        { label: 'Total', data: totalPerMod, backgroundColor: '#e0e0e0', borderRadius: 6 },
                    ],
                },
                options: {
                    responsive: true, maintainAspectRatio: false, indexAxis: 'y',
                    plugins: { legend: { position: 'bottom' } },
                    scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } },
                },
            });
        }

        // Workshop status donut
        const wsLabels = Object.keys(d.by_workshop_status || {});
        const wsData = Object.values(d.by_workshop_status || {});
        const wsColors = wsLabels.map(l => l === 'planned' ? '#0070f2' : l === 'in_progress' ? '#e76500' : l === 'completed' ? '#30914c' : '#a9b4be');

        if (wsLabels.length > 0) {
            new Chart(document.getElementById('ahWsStatusChart'), {
                type: 'doughnut',
                data: { labels: wsLabels.map(fmtStatus), datasets: [{ data: wsData, backgroundColor: wsColors }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
            });
        }

        // Analysis type bar
        const atLabels = Object.keys(d.by_analysis_type || {});
        const atData = Object.values(d.by_analysis_type || {});

        if (atLabels.length > 0) {
            new Chart(document.getElementById('ahAnalysisTypeChart'), {
                type: 'bar',
                data: {
                    labels: atLabels.map(fmtStatus),
                    datasets: [{ label: 'Count', data: atData, backgroundColor: '#1a9898', borderRadius: 6 }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
                },
            });
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    //  CRUD Modals
    // ═══════════════════════════════════════════════════════════════════════

    function showAddL2ProcessModal() {
        // Collect L1 processes from the tree as parent options
        const l1List = processTree.map(n => ({ id: n.id, name: n.name }));
        if (l1List.length === 0) {
            App.toast('Please add an L1 process first (use + Child on tree nodes)', 'warning');
            return;
        }
        App.openModal(`
            <div class="modal-header"><h2>Add L2 Process</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Parent L1 Process *</label>
                    <select id="apParentId" class="form-input">
                        ${l1List.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group"><label>Name *</label><input id="apName" class="form-input" placeholder="e.g. Purchase Requisition"></div>
                <div class="form-group"><label>Description</label><textarea id="apDesc" class="form-input" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Process ID Code</label><input id="apCode" class="form-input" placeholder="e.g. P2P-002"></div>
                    <div class="form-group"><label>Module</label><input id="apModule" class="form-input" placeholder="e.g. MM"></div>
                </div>
                <input type="hidden" id="apLevel" value="L2">
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="AnalysisView.doAddProcess()">Create</button>
            </div>
        `);
    }

    function showAddProcessModal(parentId, level) {
        const lvl = level || 'L1';
        App.openModal(`
            <div class="modal-header"><h2>Add ${lvl} Process</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label><input id="apName" class="form-input" placeholder="e.g. Sales Order Processing"></div>
                <div class="form-group"><label>Description</label><textarea id="apDesc" class="form-input" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Process ID Code</label><input id="apCode" class="form-input" placeholder="e.g. O2C-001"></div>
                    <div class="form-group"><label>Module</label><input id="apModule" class="form-input" placeholder="e.g. SD"></div>
                </div>
                <input type="hidden" id="apParentId" value="${parentId || ''}">
                <input type="hidden" id="apLevel" value="${lvl}">
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="AnalysisView.doAddProcess()">Create</button>
            </div>
        `);
    }

    async function doAddProcess() {
        const body = {
            name: document.getElementById('apName').value,
            description: document.getElementById('apDesc').value,
            process_id_code: document.getElementById('apCode').value,
            module: document.getElementById('apModule').value,
            level: document.getElementById('apLevel').value,
        };
        const parentId = document.getElementById('apParentId').value;
        if (parentId) body.parent_id = parseInt(parentId);

        try {
            await API.post(`/scenarios/${selectedScenarioId}/processes`, body);
            App.closeModal();
            App.toast('Process created', 'success');
            await loadProcessTree();
        } catch(e) { App.toast(e.message, 'error'); }
    }

    async function deleteProcess(pid) {
        if (!confirm('Delete this process and all its children?')) return;
        try {
            await API.delete(`/processes/${pid}`);
            App.toast('Process deleted', 'success');
            await loadProcessTree();
        } catch(e) { App.toast(e.message, 'error'); }
    }

    function showAddRequirementModal(processId) {
        App.openModal(`
            <div class="modal-header"><h2>Add Requirement</h2></div>
            <div class="modal-body">
                <div class="form-row">
                    <div class="form-group"><label>Code</label><input id="siCode" class="form-input" placeholder="e.g. 1YG"></div>
                    <div class="form-group"><label>Name *</label><input id="siName" class="form-input" placeholder="e.g. Domestic Sales"></div>
                </div>
                <div class="form-group"><label>Description</label><textarea id="siDesc" class="form-input" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>SAP Reference</label><input id="siRef" class="form-input" placeholder="e.g. BP-SD-01"></div>
                    <div class="form-group"><label>Module</label><input id="siModule" class="form-input" placeholder="e.g. SD"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Priority</label>
                        <select id="siPriority" class="form-input">
                            <option value="high">High</option>
                            <option value="medium" selected>Medium</option>
                            <option value="low">Low</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Fit / Gap Result *</label>
                        <select id="siFitGap" class="form-input">
                            <option value="fit">Fit</option>
                            <option value="partial_fit">Partial Fit</option>
                            <option value="gap" selected>Gap</option>
                        </select>
                    </div>
                </div>
                <div class="form-group"><label>Decision / Notes</label><textarea id="siNotes" class="form-input" rows="2" placeholder="Workshop outcome, customisation notes…"></textarea></div>
                <input type="hidden" id="siProcessId" value="${processId}">
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="AnalysisView.doAddRequirement()">Create</button>
            </div>
        `);
    }

    async function doAddRequirement() {
        const pid = parseInt(document.getElementById('siProcessId').value);
        const fitGap = document.getElementById('siFitGap').value;
        const name = document.getElementById('siName').value;
        const code = document.getElementById('siCode').value;
        const description = document.getElementById('siDesc').value;
        const module = document.getElementById('siModule').value;
        const priority = document.getElementById('siPriority').value;
        const notes = document.getElementById('siNotes').value;
        const sapRef = document.getElementById('siRef').value;

        try {
            // 1) Create a Requirement in the requirements table (single source of truth)
            const req = await API.post(`/programs/${programId}/requirements`, {
                code: code,
                title: name,
                description: description,
                req_type: 'functional',
                priority: priority === 'high' ? 'must_have' : priority === 'medium' ? 'should_have' : 'could_have',
                status: 'draft',
                source: 'process_tree',
                module: module,
                fit_gap: fitGap,
                notes: notes,
            });

            // 2) Create scope item linked to both process AND requirement
            const si = await API.post(`/processes/${pid}/scope-items`, {
                code: code,
                name: name,
                description: description,
                sap_reference: sapRef,
                module: module,
                status: 'in_scope',
                priority: priority,
                notes: notes,
                requirement_id: req.id,
            });

            // 3) Auto-create analysis with fit/gap result
            await API.post(`/scope-items/${si.id}/analyses`, {
                name: `${name} — Fit/Gap Assessment`,
                analysis_type: 'fit_gap',
                status: 'completed',
                fit_gap_result: fitGap,
                date: new Date().toISOString().slice(0, 10),
                decision: notes,
            });

            App.closeModal();
            App.toast('Requirement created (visible on all pages)', 'success');
            await selectProcess(pid);
        } catch(e) { App.toast(e.message, 'error'); }
    }

    async function deleteScopeItem(siid, processId) {
        if (!confirm('Delete this scope item and its linked requirement?')) return;
        try {
            // Get linked requirement before deleting
            const si = await API.get(`/scope-items/${siid}`);
            await API.delete(`/scope-items/${siid}`);
            // Also delete linked requirement if it was created from process tree
            if (si.requirement_id && si.requirement && si.requirement.source === 'process_tree') {
                try { await API.delete(`/requirements/${si.requirement_id}`); } catch(e) { /* ignore if already deleted */ }
            }
            App.toast('Scope item deleted', 'success');
            await selectProcess(processId);
        } catch(e) { App.toast(e.message, 'error'); }
    }

    // showAddAnalysisModal and doAddAnalysis removed — fit/gap is set via + Requirement flow


    // ── Utilities ────────────────────────────────────────────────────────
    function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
    function fmtStatus(s) { return (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
    function fmtFitGap(v) {
        const labels = { fit: 'Fit', gap: 'Gap', partial_fit: 'Partial Fit' };
        return labels[v] || fmtStatus(v);
    }


    // ── Public API ───────────────────────────────────────────────────────
    return {
        render, switchTab,
        setWsView, wsFilterByStatus, wsFilterByType, wsFilterByScenario, viewWorkshop,
        selectTreeScenario, toggleTreeNode, selectProcess, showScopeItemDetail,
        showAddL2ProcessModal, showAddProcessModal, doAddProcess, deleteProcess,
        showAddRequirementModal, doAddRequirement, deleteScopeItem,
        smFilter, quickFitGap,
        renderActiveTab,
        runAIClassify,
    };
})();
