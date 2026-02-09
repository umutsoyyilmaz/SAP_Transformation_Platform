/**
 * SAP Transformation Platform — Analysis Hub
 *
 * 4-tab view for workshops, process tree, scope matrix, and KPI dashboard.
 *
 * Tab 1: Workshop Planner   — Cross-scenario workshop calendar / kanban / list
 * Tab 2: Process Tree        — L2→L3 hierarchy (Scenario = L1)
 * Tab 3: Scope Matrix        — L3 fit/gap grid with inline analysis
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

    let selectedScenarioId = null;

    let wsViewMode = 'list';
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

    // ── Main Render ──────────────────────────────────────────────────────
    async function render() {
        const prog = App.getActiveProgram();
        if (!prog) return;
        programId = prog.id;

        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header"><h1>🔬 Analysis Hub</h1></div>
            <div class="ah-tabs">
                <button class="ah-tab ${activeTab === 'workshops' ? 'ah-tab--active' : ''}" onclick="AnalysisView.switchTab('workshops')">📅 Workshop Planner</button>
                <button class="ah-tab ${activeTab === 'process-tree' ? 'ah-tab--active' : ''}" onclick="AnalysisView.switchTab('process-tree')">🌳 Process Tree</button>
                <button class="ah-tab ${activeTab === 'scope-matrix' ? 'ah-tab--active' : ''}" onclick="AnalysisView.switchTab('scope-matrix')">📊 Scope Matrix</button>
                <button class="ah-tab ${activeTab === 'dashboard' ? 'ah-tab--active' : ''}" onclick="AnalysisView.switchTab('dashboard')">📈 Dashboard</button>
            </div>
            <div id="ahTabContent" class="ah-tab-content"></div>
        `;
        try { scenarios = await API.get(`/programs/${programId}/scenarios`); } catch(e) { scenarios = []; }
        await renderActiveTab();
    }

    function switchTab(tab) {
        activeTab = tab;
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
                    <select class="form-input form-input--sm" onchange="AnalysisView.wsFilterByScenario(this.value)"><option value="">All Scenarios</option>${scenarioOpts}</select>
                    <select class="form-input form-input--sm" onchange="AnalysisView.wsFilterByType(this.value)"><option value="">All Types</option>${Object.entries(SESSION_TYPES).map(([k,v]) => `<option value="${k}" ${wsFilterType === k ? 'selected' : ''}>${v.icon} ${v.label}</option>`).join('')}</select>
                    <select class="form-input form-input--sm" onchange="AnalysisView.wsFilterByStatus(this.value)"><option value="">All Status</option><option value="planned" ${wsFilterStatus === 'planned' ? 'selected' : ''}>Planned</option><option value="in_progress" ${wsFilterStatus === 'in_progress' ? 'selected' : ''}>In Progress</option><option value="completed" ${wsFilterStatus === 'completed' ? 'selected' : ''}>Completed</option><option value="cancelled" ${wsFilterStatus === 'cancelled' ? 'selected' : ''}>Cancelled</option></select>
                </div>
            </div>
            <div class="ah-ws-summary">
                <span class="badge badge-info">${workshops.length} workshops</span>
                <span class="badge badge-planned">${workshops.filter(w => w.status === 'planned').length} planned</span>
                <span class="badge badge-in_progress">${workshops.filter(w => w.status === 'in_progress').length} in progress</span>
                <span class="badge badge-completed">${workshops.filter(w => w.status === 'completed').length} completed</span>
            </div>
            <div id="wsViewContainer"></div>`;
        renderWsView();
    }

    function getFilteredWorkshops() {
        let f = [...workshops];
        if (wsFilterStatus) f = f.filter(w => w.status === wsFilterStatus);
        if (wsFilterType) f = f.filter(w => w.session_type === wsFilterType);
        if (wsFilterScenario) f = f.filter(w => w.scenario_id == wsFilterScenario);
        return f;
    }
    function renderWsView() { const f = getFilteredWorkshops(); const c = document.getElementById('wsViewContainer'); if (!c) return; switch(wsViewMode){ case 'list': return renderWsList(c,f); case 'kanban': return renderWsKanban(c,f); case 'calendar': return renderWsCalendar(c,f); } }

    function renderWsList(c, items) {
        if (!items.length) { c.innerHTML = '<div class="empty-state"><div class="empty-state__icon">📅</div><div class="empty-state__title">No workshops found</div></div>'; return; }
        c.innerHTML = `<table class="data-table"><thead><tr><th>Workshop</th><th>Scenario</th><th>Type</th><th>Status</th><th>Date</th><th>Facilitator</th><th>Fit/Gap/Partial</th><th>Actions</th></tr></thead><tbody>${items.map(w => { const t = SESSION_TYPES[w.session_type] || { label: w.session_type, icon: '📄', color: '#5b738b' }; const d = w.session_date ? new Date(w.session_date).toLocaleDateString('tr-TR') : '—'; return `<tr><td><strong>${esc(w.title)}</strong></td><td><span class="badge badge-info">${esc(w.scenario_name||'')}</span></td><td><span class="badge" style="background:${t.color}22;color:${t.color}">${t.icon} ${t.label}</span></td><td><span class="badge badge-${w.status}">${fmtStatus(w.status)}</span></td><td>${d}</td><td>${esc(w.facilitator||'—')}</td><td>${(w.fit_count||w.gap_count||w.partial_fit_count)?`<span class="count-fit">✓${w.fit_count||0}</span> <span class="count-gap">✗${w.gap_count||0}</span> <span class="count-partial">◐${w.partial_fit_count||0}</span>`:'—'}</td><td><button class="btn btn-secondary btn-sm" onclick="AnalysisView.viewWorkshop(${w.id},${w.scenario_id})">View</button></td></tr>`; }).join('')}</tbody></table>`;
    }

    function renderWsKanban(c, items) {
        const cols = ['planned','in_progress','completed','cancelled'];
        c.innerHTML = `<div class="ah-kanban">${cols.map(status => { const cards = items.filter(w => w.status === status); return `<div class="ah-kanban__col"><div class="ah-kanban__col-header"><span>${fmtStatus(status)}</span><span class="badge">${cards.length}</span></div><div class="ah-kanban__cards">${!cards.length?'<div class="ah-kanban__empty">No items</div>':cards.map(w => { const t = SESSION_TYPES[w.session_type]||{label:w.session_type,icon:'📄',color:'#5b738b'}; const d = w.session_date?new Date(w.session_date).toLocaleDateString('tr-TR'):''; return `<div class="ah-kanban__card" onclick="AnalysisView.viewWorkshop(${w.id},${w.scenario_id})"><div class="ah-kanban__card-type" style="border-left:4px solid ${t.color}"><strong>${esc(w.title)}</strong></div><div class="ah-kanban__card-meta"><span class="badge" style="background:${t.color}22;color:${t.color};font-size:10px">${t.icon} ${t.label}</span><span style="font-size:11px;color:var(--sap-text-secondary)">${esc(w.scenario_name||'')}</span></div>${d?`<div style="font-size:11px;color:var(--sap-text-secondary)">📅 ${d}</div>`:''}</div>`; }).join('')}</div></div>`; }).join('')}</div>`;
    }

    function renderWsCalendar(c, items) {
        const now = new Date(); const year = now.getFullYear(); const month = now.getMonth();
        const daysInMonth = new Date(year, month+1, 0).getDate();
        const firstDay = new Date(year, month, 1).getDay();
        const startOffset = firstDay === 0 ? 6 : firstDay - 1;
        const monthName = new Date(year, month).toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' });
        const dayMap = {};
        items.forEach(w => { if (!w.session_date) return; const d = new Date(w.session_date); if (d.getFullYear()===year && d.getMonth()===month) { const day=d.getDate(); if (!dayMap[day]) dayMap[day]=[]; dayMap[day].push(w); } });
        let cells = '';
        for (let i=0;i<startOffset;i++) cells+='<div class="ah-cal__cell ah-cal__cell--empty"></div>';
        for (let d=1;d<=daysInMonth;d++) { const ws=dayMap[d]||[]; const isToday=d===now.getDate()&&month===now.getMonth()&&year===now.getFullYear(); cells+=`<div class="ah-cal__cell ${isToday?'ah-cal__cell--today':''}"><span class="ah-cal__day">${d}</span>${ws.map(w=>{const t=SESSION_TYPES[w.session_type]||{icon:'📄',color:'#5b738b'}; return `<div class="ah-cal__event" style="background:${t.color}22;color:${t.color};border-left:3px solid ${t.color}" onclick="AnalysisView.viewWorkshop(${w.id},${w.scenario_id})" title="${esc(w.title)}">${t.icon} ${esc(w.title.length>15?w.title.slice(0,15)+'…':w.title)}</div>`;}).join('')}</div>`; }
        const noDate=items.filter(w=>!w.session_date);
        c.innerHTML = `<div class="ah-cal"><div class="ah-cal__header"><h3>${monthName}</h3></div><div class="ah-cal__grid"><div class="ah-cal__dow">Pzt</div><div class="ah-cal__dow">Sal</div><div class="ah-cal__dow">Çar</div><div class="ah-cal__dow">Per</div><div class="ah-cal__dow">Cum</div><div class="ah-cal__dow">Cmt</div><div class="ah-cal__dow">Paz</div>${cells}</div></div>${noDate.length?`<div class="card" style="margin-top:16px"><div class="card-header"><h3>Unscheduled (${noDate.length})</h3></div><div class="ah-unscheduled">${noDate.map(w=>{const t=SESSION_TYPES[w.session_type]||{icon:'📄',color:'#5b738b',label:w.session_type}; return `<div class="badge" style="margin:4px;cursor:pointer;background:${t.color}22;color:${t.color}" onclick="AnalysisView.viewWorkshop(${w.id},${w.scenario_id})">${t.icon} ${esc(w.title)}</div>`;}).join('')}</div></div>`:''}`;
    }

    function setWsView(m) { wsViewMode = m; renderWorkshopsTab(); }
    function wsFilterByStatus(v) { wsFilterStatus = v; renderWsView(); }
    function wsFilterByType(v) { wsFilterType = v; renderWsView(); }
    function wsFilterByScenario(v) { wsFilterScenario = v; renderWsView(); }
    function viewWorkshop(wid) { if (typeof ScenarioView !== 'undefined') ScenarioView.openWorkshop(wid); }

    // ═══════════════════════════════════════════════════════════════════════
    //  TAB 2: Process Tree  (L2 → L3, Scenario = L1)
    // ═══════════════════════════════════════════════════════════════════════

    async function renderProcessTreeTab() {
        const c = document.getElementById('ahTabContent');
        if (!scenarios.length) { c.innerHTML = '<div class="empty-state"><div class="empty-state__icon">🌳</div><div class="empty-state__title">No scenarios</div><p>Create scenarios first.</p></div>'; return; }
        if (!selectedScenarioId) selectedScenarioId = scenarios[0].id;
        c.innerHTML = `
            <div class="ah-toolbar">
                <div class="ah-toolbar__left">
                    <label style="font-weight:600;margin-right:8px">Scenario (L1):</label>
                    <select class="form-input form-input--sm" onchange="AnalysisView.selectTreeScenario(this.value)">
                        ${scenarios.map(s => `<option value="${s.id}" ${selectedScenarioId==s.id?'selected':''}>${esc(s.name)} ${s.sap_module?'('+s.sap_module+')':''}</option>`).join('')}
                    </select>
                </div>
                <div class="ah-toolbar__right">
                    <button class="btn btn-primary btn-sm" onclick="AnalysisView.showAddProcessModal(null,'L2')">+ Add L2 Process</button>
                </div>
            </div>
            <div class="ah-tree-container">
                <div class="ah-tree" id="processTreePanel"><div class="spinner"></div></div>
                <div class="ah-tree-detail" id="processDetailPanel">
                    <div class="empty-state" style="padding:40px"><div class="empty-state__icon">👈</div><div class="empty-state__title">Select a process</div><p>Click an L2 node to see its L3 steps.</p></div>
                </div>
            </div>`;
        await loadProcessTree();
    }

    async function loadProcessTree() {
        try { processTree = await API.get(`/scenarios/${selectedScenarioId}/processes?tree=true`); } catch(e) { processTree = []; }
        renderTree();
    }

    function renderTree() {
        const panel = document.getElementById('processTreePanel');
        if (!panel) return;
        if (!processTree.length) { panel.innerHTML = `<div class="empty-state" style="padding:30px"><div class="empty-state__icon">🌳</div><div class="empty-state__title">No processes yet</div><br><button class="btn btn-primary btn-sm" onclick="AnalysisView.showAddProcessModal(null,'L2')">+ Add L2 Process</button></div>`; return; }
        panel.innerHTML = renderTreeNodes(processTree, 0);
    }

    function renderTreeNodes(nodes, depth) {
        return nodes.map(n => {
            const ch = n.children || [];
            const lvlColor = n.level === 'L2' ? '#0070f2' : '#925ace';
            let badges = '';
            if (n.level === 'L3') {
                if (n.scope_decision) badges += ` <span class="badge badge-${n.scope_decision}" style="font-size:9px">${fmtStatus(n.scope_decision)}</span>`;
                if (n.fit_gap) badges += ` <span class="badge badge-${n.fit_gap}" style="font-size:9px">${fmtFitGap(n.fit_gap)}</span>`;
            }
            return `<div class="ah-tree-node" style="padding-left:${depth*20}px">
                <div class="ah-tree-node__row" onclick="AnalysisView.selectProcess(${n.id})">
                    <span class="ah-tree-node__toggle ${ch.length?'':'ah-tree-node__toggle--leaf'}" onclick="event.stopPropagation();AnalysisView.toggleTreeNode(this)">${ch.length?'▶':'•'}</span>
                    <span class="badge" style="background:${lvlColor}22;color:${lvlColor};font-size:10px;margin-right:6px">${n.level}</span>
                    <span class="ah-tree-node__name">${esc(n.name)}</span>
                    ${n.process_id_code?`<span style="color:var(--sap-text-secondary);font-size:11px;margin-left:6px">${esc(n.process_id_code)}</span>`:''}
                    ${badges}
                    <span class="ah-tree-node__actions">
                        ${n.level==='L2'?`<button class="btn btn-secondary btn-sm" style="font-size:10px;padding:2px 6px" onclick="event.stopPropagation();AnalysisView.showAddProcessModal(${n.id},'L3')">+ L3</button>`:''}
                        <button class="btn btn-danger btn-sm" style="font-size:10px;padding:2px 6px" onclick="event.stopPropagation();AnalysisView.deleteProcess(${n.id})">✗</button>
                    </span>
                </div>
                ${ch.length?`<div class="ah-tree-node__children">${renderTreeNodes(ch,depth+1)}</div>`:''}
            </div>`;
        }).join('');
    }

    function toggleTreeNode(el) {
        const node = el.closest('.ah-tree-node');
        const ch = node.querySelector('.ah-tree-node__children');
        if (!ch) return;
        const open = ch.style.display !== 'none';
        ch.style.display = open ? 'none' : 'block';
        el.textContent = open ? '▶' : '▼';
    }

    async function selectProcess(pid) {
        const panel = document.getElementById('processDetailPanel');
        panel.innerHTML = '<div class="spinner"></div>';
        try {
            const proc = await API.get(`/processes/${pid}?include_children=false`);
            if (proc.level === 'L2') {
                const children = await API.get(`/scenarios/${selectedScenarioId}/processes?parent_id=${pid}`).catch(() => []);
                const reqs = await API.get(`/programs/${programId}/requirements?process_id=${pid}`).catch(() => []);
                panel.innerHTML = `<div class="ah-scope-panel">
                    <div class="ah-scope-panel__header"><h3>${esc(proc.name)}</h3><span class="badge" style="background:#0070f222;color:#0070f2">L2 Process</span>${proc.module?`<span class="badge badge-info">${esc(proc.module)}</span>`:''}</div>
                    ${proc.description?`<p style="color:var(--sap-text-secondary);margin-bottom:12px">${esc(proc.description)}</p>`:''}
                    <div style="margin-bottom:12px">
                        <button class="btn btn-primary btn-sm" onclick="AnalysisView.showAddProcessModal(${pid},'L3')">+ Add L3 Step</button>
                        <button class="btn btn-secondary btn-sm" onclick="AnalysisView.showAddRequirementToL2(${pid})">+ Add Requirement</button>
                    </div>
                    <h4>L3 Process Steps (${(children||[]).length})</h4>
                    ${!(children||[]).length?'<p style="color:var(--sap-text-secondary);padding:8px">No L3 steps yet.</p>':`<table class="data-table"><thead><tr><th>Code</th><th>Name</th><th>Scope</th><th>Fit/Gap</th><th>SAP TCode</th><th>Priority</th></tr></thead><tbody>${children.map(ch=>`<tr class="ah-clickable-row" onclick="AnalysisView.selectProcess(${ch.id})"><td><strong>${esc(ch.code||ch.process_id_code||'—')}</strong></td><td>${esc(ch.name)}</td><td>${ch.scope_decision?`<span class="badge badge-${ch.scope_decision}">${fmtStatus(ch.scope_decision)}</span>`:'—'}</td><td>${ch.fit_gap?`<span class="badge badge-${ch.fit_gap}">${fmtFitGap(ch.fit_gap)}</span>`:'—'}</td><td>${esc(ch.sap_tcode||'—')}</td><td>${ch.priority?`<span class="badge badge-priority-${ch.priority}">${ch.priority}</span>`:'—'}</td></tr>`).join('')}</tbody></table>`}
                    <h4 style="margin-top:16px">Requirements (${(reqs||[]).length})</h4>
                    ${!(reqs||[]).length?'<p style="color:var(--sap-text-secondary);padding:8px">No requirements linked.</p>':`<table class="data-table"><thead><tr><th>Code</th><th>Title</th><th>Type</th><th>Status</th><th>Open Items</th></tr></thead><tbody>${reqs.map(r=>`<tr><td><strong>${esc(r.code)}</strong></td><td>${esc(r.title)}</td><td><span class="badge badge-info">${r.req_type}</span></td><td><span class="badge badge-${r.status}">${fmtStatus(r.status)}</span></td><td>${r.open_item_count?`<span class="badge badge-warning">${r.open_item_count}</span>`:'—'} ${r.blocker_count?`<span class="badge badge-danger">${r.blocker_count} blocker</span>`:''}</td></tr>`).join('')}</tbody></table>`}
                </div>`;
            } else if (proc.level === 'L3') {
                const analyses = await API.get(`/processes/${pid}/analyses`).catch(() => []);
                const mappings = await API.get(`/processes/${pid}/requirement-mappings`).catch(() => []);
                panel.innerHTML = `<div class="ah-scope-panel">
                    <div class="ah-scope-panel__header"><h3>${esc(proc.name)}</h3><span class="badge" style="background:#925ace22;color:#925ace">L3 Step</span>${proc.module?`<span class="badge badge-info">${esc(proc.module)}</span>`:''}</div>
                    ${proc.description?`<p style="color:var(--sap-text-secondary);margin-bottom:12px">${esc(proc.description)}</p>`:''}
                    <dl class="detail-list" style="margin-bottom:16px">
                        <dt>Code</dt><dd>${esc(proc.code||proc.process_id_code||'—')}</dd>
                        <dt>Scope Decision</dt><dd>${proc.scope_decision?`<span class="badge badge-${proc.scope_decision}">${fmtStatus(proc.scope_decision)}</span>`:'<em>Not decided</em>'}</dd>
                        <dt>Fit / Gap</dt><dd>${proc.fit_gap?`<span class="badge badge-${proc.fit_gap}">${fmtFitGap(proc.fit_gap)}</span>`:'<em>Not classified</em>'}</dd>
                        <dt>SAP TCode</dt><dd>${esc(proc.sap_tcode||'—')}</dd>
                        <dt>SAP Reference</dt><dd>${esc(proc.sap_reference||'—')}</dd>
                        <dt>Priority</dt><dd>${proc.priority?`<span class="badge badge-priority-${proc.priority}">${proc.priority}</span>`:'—'}</dd>
                    </dl>
                    <div style="margin-bottom:12px">
                        <button class="btn btn-primary btn-sm" onclick="AnalysisView.showAddAnalysisModal(${pid})">+ Analysis</button>
                        <button class="btn btn-secondary btn-sm" onclick="AnalysisView.showEditL3Modal(${pid})">Edit</button>
                        <select class="form-input form-input--sm" style="width:120px;display:inline-block" onchange="AnalysisView.quickUpdateL3(${pid},'fit_gap',this.value)"><option value="">Fit/Gap</option><option value="fit">✓ Fit</option><option value="partial_fit">◐ Partial</option><option value="gap">✗ Gap</option><option value="standard">📦 Std</option></select>
                        <select class="form-input form-input--sm" style="width:120px;display:inline-block" onchange="AnalysisView.quickUpdateL3(${pid},'scope_decision',this.value)"><option value="">Scope</option><option value="in_scope">✓ In</option><option value="out_of_scope">✗ Out</option><option value="deferred">⏸ Defer</option></select>
                    </div>
                    <h4>Requirement Mappings (${(mappings||[]).length})</h4>
                    ${!(mappings||[]).length?'<p style="color:var(--sap-text-secondary);padding:8px">No requirements mapped.</p>':`<table class="data-table"><thead><tr><th>Requirement</th><th>Coverage</th><th>Notes</th></tr></thead><tbody>${mappings.map(m=>`<tr><td>${esc(m.requirement_code||'')} — ${esc(m.requirement_title||'')}</td><td><span class="badge badge-${m.coverage_type}">${m.coverage_type}</span></td><td>${esc(m.notes||'—')}</td></tr>`).join('')}</tbody></table>`}
                    <h4 style="margin-top:16px">Analyses (${(analyses||[]).length})</h4>
                    ${!(analyses||[]).length?'<p style="color:var(--sap-text-secondary);padding:8px">No analyses.</p>':`<table class="data-table"><thead><tr><th>Name</th><th>Type</th><th>Result</th><th>Status</th><th>Date</th></tr></thead><tbody>${analyses.map(a=>`<tr><td>${esc(a.name)}</td><td>${a.analysis_type}</td><td>${a.fit_gap_result?`<span class="badge badge-${a.fit_gap_result}">${a.fit_gap_result}</span>`:'—'}</td><td><span class="badge badge-${a.status}">${fmtStatus(a.status)}</span></td><td>${a.date||'—'}</td></tr>`).join('')}</tbody></table>`}
                </div>`;
            }
        } catch(e) { panel.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`; }
    }

    function selectTreeScenario(sid) { selectedScenarioId = sid; loadProcessTree(); const dp=document.getElementById('processDetailPanel'); if(dp) dp.innerHTML='<div class="empty-state" style="padding:40px"><div class="empty-state__icon">👈</div><div class="empty-state__title">Select a process</div></div>'; }

    // ═══════════════════════════════════════════════════════════════════════
    //  TAB 3: Scope Matrix  (L3 process steps)
    // ═══════════════════════════════════════════════════════════════════════

    let smFilterModule = '';
    let smFilterScope = '';
    let smFilterResult = '';

    async function renderScopeMatrixTab() {
        const c = document.getElementById('ahTabContent');
        c.innerHTML = '<div class="spinner"></div>';
        try { scopeMatrix = await API.get(`/programs/${programId}/scope-matrix`); } catch(e) { scopeMatrix = []; }
        const modules = [...new Set(scopeMatrix.map(r => r.module).filter(Boolean))];
        const total = scopeMatrix.length;
        const fitC = scopeMatrix.filter(r => r.fit_gap === 'fit').length;
        const gapC = scopeMatrix.filter(r => r.fit_gap === 'gap').length;
        const partC = scopeMatrix.filter(r => r.fit_gap === 'partial_fit').length;
        const stdC = scopeMatrix.filter(r => r.fit_gap === 'standard').length;
        const classified = fitC + gapC + partC + stdC;
        const pct = total > 0 ? Math.round(classified / total * 100) : 0;
        c.innerHTML = `
            <div class="ah-toolbar"><div class="ah-toolbar__left">
                <select class="form-input form-input--sm" onchange="AnalysisView.smFilter('module',this.value)"><option value="">All Modules</option>${modules.map(m=>`<option value="${m}" ${smFilterModule===m?'selected':''}>${m}</option>`).join('')}</select>
                <select class="form-input form-input--sm" onchange="AnalysisView.smFilter('scope',this.value)"><option value="">All Scope</option><option value="in_scope" ${smFilterScope==='in_scope'?'selected':''}>In Scope</option><option value="out_of_scope" ${smFilterScope==='out_of_scope'?'selected':''}>Out of Scope</option><option value="deferred" ${smFilterScope==='deferred'?'selected':''}>Deferred</option></select>
                <select class="form-input form-input--sm" onchange="AnalysisView.smFilter('result',this.value)"><option value="">All Fit/Gap</option><option value="fit" ${smFilterResult==='fit'?'selected':''}>Fit</option><option value="partial_fit" ${smFilterResult==='partial_fit'?'selected':''}>Partial</option><option value="gap" ${smFilterResult==='gap'?'selected':''}>Gap</option><option value="standard" ${smFilterResult==='standard'?'selected':''}>Standard</option><option value="none" ${smFilterResult==='none'?'selected':''}>Not Classified</option></select>
            </div></div>
            <div class="ah-progress-bar"><div class="ah-progress-bar__track">
                <div class="ah-progress-bar__fill ah-progress-bar__fill--fit" style="width:${total>0?fitC/total*100:0}%"></div>
                <div class="ah-progress-bar__fill ah-progress-bar__fill--partial" style="width:${total>0?partC/total*100:0}%"></div>
                <div class="ah-progress-bar__fill ah-progress-bar__fill--gap" style="width:${total>0?gapC/total*100:0}%"></div>
            </div><div class="ah-progress-bar__labels">
                <span>Classified: <strong>${classified}/${total}</strong> (${pct}%)</span>
                <span class="count-fit">✓ Fit: ${fitC}</span><span class="count-partial">◐ Partial: ${partC}</span><span class="count-gap">✗ Gap: ${gapC}</span><span>📦 Std: ${stdC}</span>
            </div></div>
            <div id="scopeMatrixTable"></div>`;
        renderScopeMatrixTable();
    }

    function smFilter(type, val) { if(type==='module') smFilterModule=val; if(type==='scope') smFilterScope=val; if(type==='result') smFilterResult=val; renderScopeMatrixTable(); }

    function renderScopeMatrixTable() {
        let items = [...scopeMatrix];
        if (smFilterModule) items = items.filter(r => r.module === smFilterModule);
        if (smFilterScope) items = items.filter(r => r.scope_decision === smFilterScope);
        if (smFilterResult) { if (smFilterResult==='none') items=items.filter(r=>!r.fit_gap); else items=items.filter(r=>r.fit_gap===smFilterResult); }
        const c = document.getElementById('scopeMatrixTable');
        if (!c) return;
        if (!items.length) { c.innerHTML = '<div class="empty-state"><div class="empty-state__icon">📊</div><div class="empty-state__title">No L3 steps found</div></div>'; return; }
        c.innerHTML = `<table class="data-table"><thead><tr><th>Module</th><th>Scenario</th><th>L2 Process</th><th>Code</th><th>L3 Step</th><th>Scope</th><th>Fit/Gap</th><th>SAP TCode</th><th>Actions</th></tr></thead><tbody>${items.map(r=>{
            const sb = r.scope_decision?`<span class="badge badge-${r.scope_decision}">${fmtStatus(r.scope_decision)}</span>`:'<span style="color:var(--sap-text-secondary)">—</span>';
            const fb = r.fit_gap?`<span class="badge badge-${r.fit_gap}">${fmtFitGap(r.fit_gap)}</span>`:'<span style="color:var(--sap-text-secondary)">—</span>';
            return `<tr><td>${esc(r.module||'—')}</td><td>${esc(r.scenario_name||'')}</td><td>${esc(r.parent_name||'—')}</td><td><strong>${esc(r.code||r.process_id_code||'—')}</strong></td><td>${esc(r.name)}</td><td>${sb}</td><td>${fb}</td><td>${esc(r.sap_tcode||'—')}</td><td><button class="btn btn-secondary btn-sm" onclick="AnalysisView.selectProcess(${r.id});AnalysisView.switchTab('process-tree')">Detail</button> <select class="form-input form-input--sm" style="width:90px;display:inline-block" onchange="AnalysisView.quickFitGap(${r.id},this.value)"><option value="">F/G</option><option value="fit">✓Fit</option><option value="partial_fit">◐Part</option><option value="gap">✗Gap</option><option value="standard">📦Std</option></select></td></tr>`; }).join('')}</tbody></table>`;
    }

    async function quickFitGap(pid, result) {
        if (!result) return;
        try {
            await API.put(`/processes/${pid}`, { fit_gap: result });
            await API.post(`/processes/${pid}/analyses`, { name: `Quick ${result.replace('_',' ')} assessment`, analysis_type: 'fit_gap', status: 'completed', fit_gap_result: result, date: new Date().toISOString().split('T')[0] });
            App.toast(`Marked as ${result.replace('_',' ')}`, 'success');
            await renderScopeMatrixTab();
        } catch(e) { App.toast(e.message, 'error'); }
    }

    async function quickUpdateL3(pid, field, value) {
        if (!value) return;
        try { await API.put(`/processes/${pid}`, { [field]: value }); App.toast('Updated', 'success'); await selectProcess(pid); await loadProcessTree(); } catch(e) { App.toast(e.message, 'error'); }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  TAB 4: Dashboard
    // ═══════════════════════════════════════════════════════════════════════

    async function renderDashboardTab() {
        const c = document.getElementById('ahTabContent');
        c.innerHTML = '<div class="spinner"></div>';
        try { dashboardData = await API.get(`/programs/${programId}/analysis-dashboard`); } catch(e) { c.innerHTML=`<div class="empty-state"><p>Error: ${e.message}</p></div>`; return; }
        const d = dashboardData;
        const cov = d.coverage_pct || 0;
        c.innerHTML = `
            <div class="kpi-row">
                <div class="kpi-card"><div class="kpi-card__value">${d.total_l3_steps||0}</div><div class="kpi-card__label">L3 Steps</div></div>
                <div class="kpi-card"><div class="kpi-card__value">${d.analyzed_l3_steps||0}</div><div class="kpi-card__label">Analyzed</div></div>
                <div class="kpi-card"><div class="kpi-card__value" style="color:${cov>=80?'#30914c':cov>=50?'#e76500':'#bb0000'}">${cov}%</div><div class="kpi-card__label">Coverage</div></div>
                <div class="kpi-card"><div class="kpi-card__value">${d.total_workshops||0}</div><div class="kpi-card__label">Workshops</div></div>
                <div class="kpi-card"><div class="kpi-card__value">${d.total_open_items||0}</div><div class="kpi-card__label">Open Items</div></div>
                <div class="kpi-card"><div class="kpi-card__value" style="color:${(d.blocker_open_items||0)>0?'#bb0000':'#30914c'}">${d.blocker_open_items||0}</div><div class="kpi-card__label">Blockers</div></div>
            </div>
            <div class="ah-alerts">
                ${(d.blocker_open_items||0)>0?`<div class="ah-alert ah-alert--danger">🔴 <strong>${d.blocker_open_items}</strong> blocker open items</div>`:''}
                ${(d.by_workshop_status?.planned||0)>0?`<div class="ah-alert ah-alert--info">📅 <strong>${d.by_workshop_status.planned}</strong> workshops planned</div>`:''}
            </div>
            <div class="dashboard-grid">
                <div class="card"><div class="card-header"><h2>Fit / Gap</h2></div><canvas id="ahFitGapChart" height="250"></canvas></div>
                <div class="card"><div class="card-header"><h2>Scope Decisions</h2></div><canvas id="ahScopeChart" height="250"></canvas></div>
            </div>
            <div class="dashboard-grid">
                <div class="card"><div class="card-header"><h2>Workshop Status</h2></div><canvas id="ahWsChart" height="220"></canvas></div>
                <div class="card"><div class="card-header"><h2>Analysis Types</h2></div><canvas id="ahAtChart" height="220"></canvas></div>
            </div>`;
        renderDashboardCharts(d);
    }

    function renderDashboardCharts(d) {
        if (typeof Chart === 'undefined') return;
        const fgD = d.by_fit_gap_l3 || d.by_fit_gap || {};
        const fgL = Object.keys(fgD); const fgV = Object.values(fgD);
        const fgC = fgL.map(l => l==='fit'?'#30914c':l==='partial_fit'?'#e76500':l==='gap'?'#bb0000':l==='standard'?'#0070f2':'#a9b4be');
        if (fgL.length) new Chart(document.getElementById('ahFitGapChart'),{type:'doughnut',data:{labels:fgL.map(fmtFitGap),datasets:[{data:fgV,backgroundColor:fgC}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom'}}}});

        const sdD = d.by_scope_decision || {};
        const sdL = Object.keys(sdD); const sdV = Object.values(sdD);
        const sdC = sdL.map(l => l==='in_scope'?'#30914c':l==='out_of_scope'?'#bb0000':l==='deferred'?'#e76500':'#a9b4be');
        if (sdL.length) new Chart(document.getElementById('ahScopeChart'),{type:'doughnut',data:{labels:sdL.map(fmtStatus),datasets:[{data:sdV,backgroundColor:sdC}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom'}}}});

        const wsD = d.by_workshop_status || {};
        const wsL = Object.keys(wsD); const wsV = Object.values(wsD);
        const wsC = wsL.map(l => l==='planned'?'#0070f2':l==='in_progress'?'#e76500':l==='completed'?'#30914c':'#a9b4be');
        if (wsL.length) new Chart(document.getElementById('ahWsChart'),{type:'doughnut',data:{labels:wsL.map(fmtStatus),datasets:[{data:wsV,backgroundColor:wsC}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom'}}}});

        const atD = d.by_analysis_type || {};
        const atL = Object.keys(atD); const atV = Object.values(atD);
        if (atL.length) new Chart(document.getElementById('ahAtChart'),{type:'bar',data:{labels:atL.map(fmtStatus),datasets:[{label:'Count',data:atV,backgroundColor:'#1a9898',borderRadius:6}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{stepSize:1}}}}});
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  CRUD Modals
    // ═══════════════════════════════════════════════════════════════════════

    function showAddProcessModal(parentId, level) {
        const lvl = level || 'L2';
        const isL3 = lvl === 'L3';
        App.openModal(`
            <div class="modal-header"><h2>Add ${lvl} ${isL3?'Process Step':'Process'}</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label><input id="apName" class="form-input"></div>
                <div class="form-group"><label>Description</label><textarea id="apDesc" class="form-input" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>${isL3?'Code':'Process ID Code'}</label><input id="apCode" class="form-input"></div>
                    <div class="form-group"><label>Module</label><input id="apModule" class="form-input"></div>
                </div>
                ${isL3?`<div class="form-row">
                    <div class="form-group"><label>Scope</label><select id="apScope" class="form-input"><option value="">—</option><option value="in_scope">In Scope</option><option value="out_of_scope">Out of Scope</option><option value="deferred">Deferred</option></select></div>
                    <div class="form-group"><label>Fit/Gap</label><select id="apFG" class="form-input"><option value="">—</option><option value="fit">Fit</option><option value="partial_fit">Partial Fit</option><option value="gap">Gap</option><option value="standard">Standard</option></select></div>
                </div><div class="form-row">
                    <div class="form-group"><label>SAP TCode</label><input id="apTCode" class="form-input"></div>
                    <div class="form-group"><label>SAP Reference</label><input id="apRef" class="form-input"></div>
                </div><div class="form-group"><label>Priority</label><select id="apPrio" class="form-input"><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option><option value="low">Low</option></select></div>`:''}
                <div class="form-group"><label>Notes</label><textarea id="apNotes" class="form-input" rows="2"></textarea></div>
                <input type="hidden" id="apParent" value="${parentId||''}"><input type="hidden" id="apLevel" value="${lvl}">
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="AnalysisView.doAddProcess()">Create</button>
            </div>`);
    }

    async function doAddProcess() {
        const level = document.getElementById('apLevel').value;
        const body = { name: document.getElementById('apName').value, description: document.getElementById('apDesc').value, module: document.getElementById('apModule').value, level, notes: document.getElementById('apNotes')?.value||'' };
        const parentId = document.getElementById('apParent').value;
        if (parentId) body.parent_id = parseInt(parentId);
        if (level === 'L3') { body.code = document.getElementById('apCode').value; body.scope_decision = document.getElementById('apScope')?.value||''; body.fit_gap = document.getElementById('apFG')?.value||''; body.sap_tcode = document.getElementById('apTCode')?.value||''; body.sap_reference = document.getElementById('apRef')?.value||''; body.priority = document.getElementById('apPrio')?.value||'medium'; }
        else { body.process_id_code = document.getElementById('apCode').value; }
        try { await API.post(`/scenarios/${selectedScenarioId}/processes`, body); App.closeModal(); App.toast(`${level} created`, 'success'); await loadProcessTree(); } catch(e) { App.toast(e.message, 'error'); }
    }

    async function deleteProcess(pid) {
        if (!confirm('Delete this process and children?')) return;
        try { await API.delete(`/processes/${pid}`); App.toast('Deleted', 'success'); await loadProcessTree(); } catch(e) { App.toast(e.message, 'error'); }
    }

    function showEditL3Modal(pid) {
        API.get(`/processes/${pid}`).then(p => {
            App.openModal(`
                <div class="modal-header"><h2>Edit L3: ${esc(p.name)}</h2></div>
                <div class="modal-body">
                    <div class="form-group"><label>Name *</label><input id="elName" class="form-input" value="${esc(p.name)}"></div>
                    <div class="form-group"><label>Description</label><textarea id="elDesc" class="form-input" rows="2">${esc(p.description||'')}</textarea></div>
                    <div class="form-row"><div class="form-group"><label>Code</label><input id="elCode" class="form-input" value="${esc(p.code||'')}"></div><div class="form-group"><label>Module</label><input id="elMod" class="form-input" value="${esc(p.module||'')}"></div></div>
                    <div class="form-row"><div class="form-group"><label>Scope</label><select id="elScope" class="form-input"><option value="">—</option><option value="in_scope" ${p.scope_decision==='in_scope'?'selected':''}>In Scope</option><option value="out_of_scope" ${p.scope_decision==='out_of_scope'?'selected':''}>Out of Scope</option><option value="deferred" ${p.scope_decision==='deferred'?'selected':''}>Deferred</option></select></div><div class="form-group"><label>Fit/Gap</label><select id="elFG" class="form-input"><option value="">—</option><option value="fit" ${p.fit_gap==='fit'?'selected':''}>Fit</option><option value="partial_fit" ${p.fit_gap==='partial_fit'?'selected':''}>Partial</option><option value="gap" ${p.fit_gap==='gap'?'selected':''}>Gap</option><option value="standard" ${p.fit_gap==='standard'?'selected':''}>Standard</option></select></div></div>
                    <div class="form-row"><div class="form-group"><label>SAP TCode</label><input id="elTC" class="form-input" value="${esc(p.sap_tcode||'')}"></div><div class="form-group"><label>SAP Ref</label><input id="elRef" class="form-input" value="${esc(p.sap_reference||'')}"></div></div>
                    <div class="form-group"><label>Priority</label><select id="elPrio" class="form-input"><option value="low" ${p.priority==='low'?'selected':''}>Low</option><option value="medium" ${p.priority==='medium'?'selected':''}>Medium</option><option value="high" ${p.priority==='high'?'selected':''}>High</option><option value="critical" ${p.priority==='critical'?'selected':''}>Critical</option></select></div>
                    <div class="form-group"><label>Notes</label><textarea id="elNotes" class="form-input" rows="2">${esc(p.notes||'')}</textarea></div>
                </div>
                <div class="modal-footer"><button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button><button class="btn btn-primary" onclick="AnalysisView.doEditL3(${pid})">Save</button></div>`);
        }).catch(e => App.toast(e.message, 'error'));
    }

    async function doEditL3(pid) {
        try {
            await API.put(`/processes/${pid}`, { name:document.getElementById('elName').value, description:document.getElementById('elDesc').value, code:document.getElementById('elCode').value, module:document.getElementById('elMod').value, scope_decision:document.getElementById('elScope').value, fit_gap:document.getElementById('elFG').value, sap_tcode:document.getElementById('elTC').value, sap_reference:document.getElementById('elRef').value, priority:document.getElementById('elPrio').value, notes:document.getElementById('elNotes').value });
            App.closeModal(); App.toast('Updated','success'); await selectProcess(pid); await loadProcessTree();
        } catch(e) { App.toast(e.message,'error'); }
    }

    function showAddRequirementToL2(processId) {
        App.openModal(`
            <div class="modal-header"><h2>Add Requirement (Workshop Output)</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Title *</label><input id="arTitle" class="form-input"></div>
                <div class="form-group"><label>Description</label><textarea id="arDesc" class="form-input" rows="2"></textarea></div>
                <div class="form-row"><div class="form-group"><label>Type</label><select id="arType" class="form-input"><option value="functional">Functional</option><option value="business">Business</option><option value="technical">Technical</option><option value="non_functional">Non-Functional</option><option value="integration">Integration</option></select></div><div class="form-group"><label>Priority</label><select id="arPrio" class="form-input"><option value="must_have">Must Have</option><option value="should_have" selected>Should Have</option><option value="could_have">Could Have</option><option value="wont_have">Won't Have</option></select></div></div>
                <div class="form-row"><div class="form-group"><label>Module</label><input id="arMod" class="form-input"></div><div class="form-group"><label>Source</label><input id="arSrc" class="form-input"></div></div>
                <div class="form-group"><label>Notes</label><textarea id="arNotes" class="form-input" rows="2"></textarea></div>
                <input type="hidden" id="arPid" value="${processId}">
            </div>
            <div class="modal-footer"><button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button><button class="btn btn-primary" onclick="AnalysisView.doAddRequirementToL2()">Create</button></div>`);
    }

    async function doAddRequirementToL2() {
        const pid = parseInt(document.getElementById('arPid').value);
        try {
            await API.post(`/programs/${programId}/requirements`, { title:document.getElementById('arTitle').value, description:document.getElementById('arDesc').value, req_type:document.getElementById('arType').value, priority:document.getElementById('arPrio').value, module:document.getElementById('arMod').value, source:document.getElementById('arSrc').value, notes:document.getElementById('arNotes').value, process_id:pid, status:'draft' });
            App.closeModal(); App.toast('Requirement created','success'); await selectProcess(pid);
        } catch(e) { App.toast(e.message,'error'); }
    }

    function showAddAnalysisModal(processId) {
        App.openModal(`
            <div class="modal-header"><h2>Add Analysis</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label><input id="anName" class="form-input"></div>
                <div class="form-group"><label>Description</label><textarea id="anDesc" class="form-input" rows="2"></textarea></div>
                <div class="form-row"><div class="form-group"><label>Type</label><select id="anType" class="form-input"><option value="workshop">Workshop</option><option value="fit_gap" selected>Fit-Gap</option><option value="demo">Demo</option><option value="prototype">Prototype</option><option value="review">Review</option></select></div><div class="form-group"><label>Result</label><select id="anRes" class="form-input"><option value="">—</option><option value="fit">Fit</option><option value="partial_fit">Partial</option><option value="gap">Gap</option></select></div></div>
                <div class="form-row"><div class="form-group"><label>Status</label><select id="anStat" class="form-input"><option value="planned">Planned</option><option value="in_progress">In Progress</option><option value="completed" selected>Completed</option></select></div><div class="form-group"><label>Date</label><input id="anDate" type="date" class="form-input" value="${new Date().toISOString().split('T')[0]}"></div></div>
                <div class="form-group"><label>Decision</label><textarea id="anDec" class="form-input" rows="2"></textarea></div>
                <input type="hidden" id="anPid" value="${processId}">
            </div>
            <div class="modal-footer"><button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button><button class="btn btn-primary" onclick="AnalysisView.doAddAnalysis()">Create</button></div>`);
    }

    async function doAddAnalysis() {
        const pid = parseInt(document.getElementById('anPid').value);
        try {
            await API.post(`/processes/${pid}/analyses`, { name:document.getElementById('anName').value, description:document.getElementById('anDesc').value, analysis_type:document.getElementById('anType').value, fit_gap_result:document.getElementById('anRes').value, status:document.getElementById('anStat').value, date:document.getElementById('anDate').value, decision:document.getElementById('anDec').value });
            App.closeModal(); App.toast('Analysis created','success'); await selectProcess(pid);
        } catch(e) { App.toast(e.message,'error'); }
    }

    // ── Utilities ────────────────────────────────────────────────────────
    function esc(s) { const d = document.createElement('div'); d.textContent = s||''; return d.innerHTML; }
    function fmtStatus(s) { return (s||'').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()); }
    function fmtFitGap(v) { return { fit:'Fit', gap:'Gap', partial_fit:'Partial Fit', standard:'Standard' }[v] || fmtStatus(v); }

    return {
        render, switchTab,
        setWsView, wsFilterByStatus, wsFilterByType, wsFilterByScenario, viewWorkshop,
        selectTreeScenario, toggleTreeNode, selectProcess,
        showAddProcessModal, doAddProcess, deleteProcess,
        showEditL3Modal, doEditL3,
        showAddRequirementToL2, doAddRequirementToL2,
        showAddAnalysisModal, doAddAnalysis,
        smFilter, quickFitGap, quickUpdateL3,
        renderActiveTab,
    };
})();
