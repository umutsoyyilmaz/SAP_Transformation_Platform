/**
 * SAP Transformation Management Platform
 * Test Planning View — Catalog + Suites
 * Extracted from testing.js (Sprint refactor)
 */

const TestPlanningView = (() => {
    const esc = TestingShared.esc;
    let currentTab = 'catalog';

    // State
    let testCases = [];
    let testSuites = [];

    // ── Filter state (persisted across re-renders) ────────────────────
    let _catalogSearch = '';
    let _catalogFilters = {};
    let _catalogTreeFilter = 'all';
    let _planSearch = '';
    let _planTreeFilter = 'all';
    let _suiteSearch = '';
    let _suiteFilters = {};
    let _suiteTreeFilter = 'all';

    // ── Structured Step state ──────────────────────────────────────────
    let _currentSteps = [];
    let _currentCaseIdForSteps = null;
    let _draftSteps = [];

    // ── ADR-008 B: Hierarchical traceability state ─────────────────────
    let _traceabilityState = { groups: [] };
    let _traceabilityOptions = {
        processLevels: [],
        requirements: [],
        backlogItems: [],
        configItems: [],
    };
    let _caseWizardStep = 1;
    let _activeTraceGroupIndex = null;
    let _activeCaseId = null;
    let _derivedTraceability = null;
    let _l3CoverageState = {
        selectedL3: null,
        cache: {},
    };

    // ── Main render ───────────────────────────────────────────────────
    async function render() {
        const pid = TestingShared.getProgram();
        const main = document.getElementById('mainContent');

        if (!pid) {
            main.innerHTML = TestingShared.noProgramHtml('Test Planning');
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{label:'Programs',onclick:'App.navigate("programs")'},{label:'Test Planning'}])}
                <h2 class="pg-view-title">Test Planning</h2>
            </div>
            <div id="testPlanningTabs"></div>
            <div class="card" id="testContent">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>
        `;
        _renderTopTabs();
        await loadTabData();
    }

    function _renderTopTabs() {
        const container = document.getElementById('testPlanningTabs');
        if (!container || !window.TMTabBar) return;
        TMTabBar.render(container, {
            active: currentTab,
            tabs: [
                { id: 'catalog', label: '📋 Test Cases' },
                { id: 'suites', label: '📦 Test Suites' },
                { id: 'plans', label: '📅 Test Plans' },
            ],
            onChange: switchTab,
        });
    }

    function switchTab(tab) {
        currentTab = tab;
        _renderTopTabs();
        if (TestingShared.pid) loadTabData();
    }

    async function loadTabData() {
        const container = document.getElementById('testContent');
        container.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';
        try {
            switch (currentTab) {
                case 'catalog': await renderCatalog(); break;
                case 'suites': await renderSuites(); break;
                case 'plans': await renderPlans(); break;
            }
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TEST PLANS TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderPlans() {
        const pid = TestingShared.pid;
        const res = await API.get(`/programs/${pid}/testing/plans`);
        const plans = res.items || res || [];
        const container = document.getElementById('testContent');

        if (plans.length === 0) {
            container.innerHTML = PGEmptyState.html({ icon: 'test', title: 'No test plans yet', description: 'Create your first test plan, then add scope (L3 process, scenario, requirement).', action: { label: '+ New Test Plan', onclick: 'TestPlanningView.showPlanModal()' } });
            return;
        }

        container.innerHTML = `
            <div class="tm-toolbar">
                <div class="tm-toolbar__left">
                    <input id="tmPlanSearch" class="tm-input" placeholder="Search test plans..." value="${esc(_planSearch)}" />
                    <span id="planItemCount" class="tm-muted"></span>
                </div>
                <div class="tm-toolbar__right">
                    <button class="btn btn-primary btn-sm" onclick="TestPlanningView.showPlanModal()">+ New Test Plan</button>
                </div>
            </div>
            <div id="planSplitRoot"></div>
        `;

        const searchEl = document.getElementById('tmPlanSearch');
        if (searchEl) {
            searchEl.addEventListener('input', (e) => {
                _planSearch = e.target.value || '';
                applyPlanFilter(plans);
            });
        }

        applyPlanFilter(plans);
    }

    function applyPlanFilter(sourcePlans) {
        let filtered = [...(sourcePlans || [])];

        if (_planSearch) {
            const q = _planSearch.toLowerCase();
            filtered = filtered.filter(p =>
                (p.name || '').toLowerCase().includes(q) ||
                (p.description || '').toLowerCase().includes(q) ||
                (p.environment || '').toLowerCase().includes(q)
            );
        }

        if (_planTreeFilter && _planTreeFilter !== 'all') {
            const [kind, value] = String(_planTreeFilter).split(':');
            if (kind === 'type') filtered = filtered.filter(p => String(p.plan_type || '') === value);
            if (kind === 'status') filtered = filtered.filter(p => String(p.status || '') === value);
            if (kind === 'env') filtered = filtered.filter(p => String(p.environment || '') === value);
        }

        const countEl = document.getElementById('planItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${(sourcePlans || []).length}`;

        _renderPlanSplit(sourcePlans || [], filtered);
    }

    function _buildPlanTreeNodes(plans) {
        const nodes = [{ id: 'all', label: 'All Plans', count: plans.length }];
        const types = new Map();
        const statuses = new Map();
        const envs = new Map();

        plans.forEach(p => {
            const t = p.plan_type || 'unknown';
            const s = p.status || 'unknown';
            const e = p.environment || 'unset';
            types.set(t, (types.get(t) || 0) + 1);
            statuses.set(s, (statuses.get(s) || 0) + 1);
            envs.set(e, (envs.get(e) || 0) + 1);
        });

        [...types.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([val, count]) => {
            nodes.push({ id: `type:${val}`, label: `Type: ${val.toUpperCase()}`, count });
        });
        [...statuses.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([val, count]) => {
            nodes.push({ id: `status:${val}`, label: `Status: ${val}`, count });
        });
        [...envs.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([val, count]) => {
            nodes.push({ id: `env:${val}`, label: `Env: ${val.toUpperCase()}`, count });
        });

        return nodes;
    }

    function _renderPlanSplit(allPlans, list) {
        const root = document.getElementById('planSplitRoot');
        if (!root) return;

        if (!window.TMSplitPane || !window.TMTreePanel || !window.TMDataGrid) {
            root.innerHTML = '<div class="empty-state" style="padding:30px">Component fallback unavailable.</div>';
            return;
        }

        TMSplitPane.mount(root, {
            leftHtml: '<div id="tmPlanTree"></div>',
            rightHtml: '<div id="tmPlanGrid" style="padding:8px"></div>',
            leftWidth: 260,
            minLeft: 180,
            maxLeft: 420,
        });

        const treeEl = document.getElementById('tmPlanTree');
        const gridEl = document.getElementById('tmPlanGrid');
        if (!treeEl || !gridEl) return;

        TMTreePanel.render(treeEl, {
            title: 'Plan Groups',
            nodes: _buildPlanTreeNodes(allPlans),
            selectedId: _planTreeFilter,
            searchPlaceholder: 'Search group...',
            onSelect: (nodeId) => {
                _planTreeFilter = nodeId;
                applyPlanFilter(allPlans);
            },
        });

        const STATUS_CLR = { draft: '#888', active: '#0070f3', completed: '#107e3e', cancelled: '#c4314b' };
        const TYPE_LBL = { sit: 'SIT', uat: 'UAT', regression: 'Regression', e2e: 'E2E', cutover_rehearsal: 'Cutover', performance: 'Performance' };

        TMDataGrid.render(gridEl, {
            rows: list,
            rowKey: 'id',
            emptyText: 'No plans match your filters.',
            onRowClick: (rowId) => TestPlanDetailView.open(Number(rowId), { from: 'planning' }),
            columns: [
                { key: 'name', label: 'Plan Name', width: '260px', render: (p) => `<strong>${esc(p.name || '-')}</strong>${p.description ? `<div style="font-size:11px;color:#64748b">${esc(p.description)}</div>` : ''}` },
                { key: 'plan_type', label: 'Type', width: '95px', render: (p) => PGStatusRegistry.badge(p.plan_type, { label: TYPE_LBL[p.plan_type] || (p.plan_type || '—').toUpperCase() }) },
                { key: 'environment', label: 'Env', width: '80px', render: (p) => p.environment ? PGStatusRegistry.badge('env', { label: esc(p.environment) }) : '-' },
                { key: 'status', label: 'Status', width: '95px', render: (p) => PGStatusRegistry.badge(p.status) },
                { key: 'start_date', label: 'Start', width: '95px', render: (p) => esc(p.start_date || '-') },
                { key: 'end_date', label: 'End', width: '95px', render: (p) => esc(p.end_date || '-') },
                {
                    key: 'actions', label: '', width: '92px', align: 'center', render: (p) =>
                        `<button class="btn btn-sm" style="background:#C08B5C;color:#fff" onclick="event.stopPropagation();TestPlanDetailView.open(${p.id}, {from:'planning'})">📊</button>
                         <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();TestPlanningView.deletePlan(${p.id})">🗑</button>`,
                },
            ],
        });
    }

    function showPlanModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>New Test Plan</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Plan Name *</label>
                    <input id="planName" class="form-control" placeholder="e.g. SIT Master Plan"></div>
                <div class="form-group"><label>Description</label>
                    <textarea id="planDesc" class="form-control" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Plan Type *</label>
                        <select id="planType" class="form-control">
                            <option value="sit">SIT — System Integration Test</option>
                            <option value="uat">UAT — User Acceptance Test</option>
                            <option value="regression">Regression</option>
                            <option value="e2e">E2E — End-to-End</option>
                            <option value="cutover_rehearsal">Cutover Rehearsal</option>
                            <option value="performance">Performance</option>
                        </select></div>
                    <div class="form-group"><label>Environment</label>
                        <select id="planEnv" class="form-control">
                            <option value="">— Select —</option>
                            <option value="DEV">DEV</option>
                            <option value="QAS">QAS</option>
                            <option value="PRE">PRE-PROD</option>
                            <option value="PRD">PRD</option>
                        </select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Start Date</label>
                        <input id="planStart" type="date" class="form-control"></div>
                    <div class="form-group"><label>End Date</label>
                        <input id="planEnd" type="date" class="form-control"></div>
                </div>
                <div class="form-group"><label>Entry Criteria</label>
                    <textarea id="planEntry" class="form-control" rows="2" placeholder="Conditions that must be met before testing begins"></textarea></div>
                <div class="form-group"><label>Exit Criteria</label>
                    <textarea id="planExit" class="form-control" rows="2" placeholder="Conditions to close this test plan"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanningView.savePlan()">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function savePlan() {
        const pid = TestingShared.pid;
        const body = {
            name: document.getElementById('planName').value,
            description: document.getElementById('planDesc').value,
            plan_type: document.getElementById('planType').value,
            environment: document.getElementById('planEnv').value || null,
            start_date: document.getElementById('planStart').value || null,
            end_date: document.getElementById('planEnd').value || null,
            entry_criteria: document.getElementById('planEntry').value,
            exit_criteria: document.getElementById('planExit').value,
        };
        if (!body.name) return App.toast('Plan name is required', 'error');
        try {
            const created = await API.post(`/programs/${pid}/testing/plans`, body);
            App.toast('Test plan created! Redirecting to detail view to add scope…', 'success');
            App.closeModal();
            // Auto-navigate to plan detail so user can add scope
            TestPlanDetailView.open(created.id, {from:'planning'});
        } catch (e) {
            App.toast(e.message || 'Failed to create plan', 'error');
        }
    }

    async function deletePlan(id) {
        if (!confirm('Delete this test plan and all its cycles?')) return;
        await API.delete(`/testing/plans/${id}`);
        App.toast('Test plan deleted', 'success');
        await renderPlans();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // CATALOG TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderCatalog() {
        const pid = TestingShared.pid;
        const res = await API.get(`/programs/${pid}/testing/catalog`);
        testCases = res.items || res || [];
        const container = document.getElementById('testContent');

        if (testCases.length === 0) {
            container.innerHTML = PGEmptyState.html({ icon: 'test', title: 'No test cases found', description: 'Add your first test case to build the test catalog.', action: { label: '+ New Test Case', onclick: 'TestPlanningView.showCaseModal()' } });
            return;
        }

        container.innerHTML = `
            <div class="tm-toolbar">
                <div class="tm-toolbar__left">
                    <input id="tmCatalogSearch" class="tm-input" placeholder="Search test cases..." value="${esc(_catalogSearch)}" />
                    <span id="catItemCount" class="tm-muted"></span>
                </div>
                <div class="tm-toolbar__right">
                    <button class="btn btn-primary btn-sm" onclick="TestPlanningView.showCaseModal()">+ New Test Case</button>
                </div>
            </div>
            <div id="catalogSplitRoot"></div>
        `;
        const searchEl = document.getElementById('tmCatalogSearch');
        if (searchEl) {
            searchEl.addEventListener('input', (e) => {
                _catalogSearch = e.target.value || '';
                applyCatalogFilter();
            });
        }
        applyCatalogFilter();
    }

    function renderCatalogFilterBar() {
        const el = document.getElementById('catalogFilterBar');
        if (!el) return;
        el.innerHTML = ExpUI.filterBar({
            id: 'catFB',
            searchPlaceholder: 'Search test cases…',
            searchValue: _catalogSearch,
            onSearch: 'TestPlanningView.setCatalogSearch(this.value)',
            onChange: 'TestPlanningView.onCatalogFilterChange',
            filters: [
                {
                    id: 'test_layer', label: 'Layer', type: 'multi', color: '#0070f3',
                    options: ['unit','sit','uat','e2e','regression','performance','cutover_rehearsal'].map(l => ({ value: l, label: l.toUpperCase() })),
                    selected: _catalogFilters.test_layer || [],
                },
                {
                    id: 'status', label: 'Status', type: 'multi', color: '#10b981',
                    options: ['draft','ready','in_review','approved','deprecated'].map(s => ({ value: s, label: s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') })),
                    selected: _catalogFilters.status || [],
                },
                {
                    id: 'priority', label: 'Priority', type: 'multi', color: '#ef4444',
                    options: ['critical','high','medium','low'].map(p => ({ value: p, label: p.charAt(0).toUpperCase() + p.slice(1) })),
                    selected: _catalogFilters.priority || [],
                },
                {
                    id: 'module', label: 'Module', type: 'multi', color: '#8b5cf6',
                    options: [...new Set(testCases.map(tc => tc.module).filter(Boolean))].sort().map(m => ({ value: m, label: m })),
                    selected: _catalogFilters.module || [],
                },
            ],
            actionsHtml: `<span style="font-size:12px;color:#94a3b8" id="catItemCount"></span>
                <button class="btn btn-primary btn-sm" onclick="TestPlanningView.showCaseModal()">+ New Test Case</button>`,
        });
    }

    function setCatalogSearch(val) {
        _catalogSearch = val;
        applyCatalogFilter();
    }

    function onCatalogFilterChange(update) {
        if (update._clearAll) {
            _catalogFilters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete _catalogFilters[key];
                } else {
                    _catalogFilters[key] = val;
                }
            });
        }
        renderCatalogFilterBar();
        applyCatalogFilter();
    }

    function applyCatalogFilter() {
        let filtered = [...testCases];

        if (_catalogSearch) {
            const q = _catalogSearch.toLowerCase();
            filtered = filtered.filter(tc =>
                (tc.title || '').toLowerCase().includes(q) ||
                (tc.code || '').toLowerCase().includes(q) ||
                (tc.module || '').toLowerCase().includes(q) ||
                (tc.assigned_to || '').toLowerCase().includes(q)
            );
        }

        Object.entries(_catalogFilters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (values.length === 0) return;
            filtered = filtered.filter(tc => values.includes(String(tc[key])));
        });

        if (_catalogTreeFilter && _catalogTreeFilter !== 'all') {
            const [kind, value] = String(_catalogTreeFilter).split(':');
            if (kind === 'module') {
                filtered = filtered.filter(tc => String(tc.module || '') === value);
            }
            if (kind === 'layer') {
                filtered = filtered.filter(tc => String(tc.test_layer || '') === value);
            }
        }

        const countEl = document.getElementById('catItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${testCases.length}`;

        _renderCatalogSplit(filtered);
    }

    function _buildCatalogTreeNodes() {
        const nodes = [{ id: 'all', label: 'All Test Cases', count: testCases.length }];

        const modules = new Map();
        const layers = new Map();
        testCases.forEach(tc => {
            const module = (tc.module || '').trim();
            const layer = (tc.test_layer || '').trim();
            if (module) modules.set(module, (modules.get(module) || 0) + 1);
            if (layer) layers.set(layer, (layers.get(layer) || 0) + 1);
        });

        [...modules.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([module, count]) => {
            nodes.push({ id: `module:${module}`, label: `Module: ${module}`, count });
        });

        [...layers.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([layer, count]) => {
            nodes.push({ id: `layer:${layer}`, label: `Layer: ${layer.toUpperCase()}`, count });
        });

        return nodes;
    }

    function _renderCatalogSplit(list) {
        const root = document.getElementById('catalogSplitRoot');
        if (!root) return;

        if (!window.TMSplitPane || !window.TMTreePanel || !window.TMDataGrid) {
            root.innerHTML = _renderCatalogTable(list);
            return;
        }

        TMSplitPane.mount(root, {
            leftHtml: '<div id="tmCatalogTree"></div>',
            rightHtml: '<div id="tmCatalogGrid" style="padding:8px"></div>',
            leftWidth: 260,
            minLeft: 180,
            maxLeft: 440,
        });

        const treeEl = document.getElementById('tmCatalogTree');
        const gridEl = document.getElementById('tmCatalogGrid');
        if (!treeEl || !gridEl) return;

        TMTreePanel.render(treeEl, {
            title: 'Catalog Groups',
            nodes: _buildCatalogTreeNodes(),
            selectedId: _catalogTreeFilter,
            searchPlaceholder: 'Search group...',
            onSelect: (nodeId) => {
                _catalogTreeFilter = nodeId;
                applyCatalogFilter();
            },
        });

        const layerBadge = (layer) => PGStatusRegistry.badge(layer, { label: (layer || 'N/A').toUpperCase() });
        const statusBadge = (status) => PGStatusRegistry.badge(status);

        TMDataGrid.render(gridEl, {
            rows: list,
            rowKey: 'id',
            emptyText: 'No test cases match your filters.',
            onRowClick: (rowId) => TestPlanningView.showCaseDetail(Number(rowId)),
            columns: [
                { key: 'code', label: 'Code', width: '140px', render: (tc) => `<span style="font-family:'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;font-weight:500;color:#1e3a5f;letter-spacing:-0.2px">${esc(tc.code || '-')}</span>` },
                { key: 'title', label: 'Title', width: 'auto' },
                { key: 'test_layer', label: 'Layer', width: '95px', render: (tc) => layerBadge(tc.test_layer) },
                { key: 'module', label: 'Module', width: '90px', render: (tc) => esc(tc.module || '-') },
                { key: 'status', label: 'Status', width: '95px', render: (tc) => statusBadge(tc.status) },
                { key: 'priority', label: 'Priority', width: '80px', render: (tc) => esc(tc.priority || '-') },
                {
                    key: 'actions', label: '', width: '50px', align: 'center',
                    render: (tc) => `<button class="btn btn-sm btn-danger" onclick="event.stopPropagation();TestPlanningView.deleteCase(${tc.id})">🗑</button>`,
                },
            ],
        });
    }

    // Legacy shim — old server-side filter, now handled client-side
    async function filterCatalog() { applyCatalogFilter(); }

    function _renderCatalogTable(list) {
        const layerBadge = (l) => PGStatusRegistry.badge(l, { label: (l || 'N/A').toUpperCase() });
        const statusBadge = (s) => PGStatusRegistry.badge(s);
        return `<table class="data-table">
                <thead><tr>
                    <th>Code</th><th>Title</th><th>Layer</th><th>Module</th><th>Status</th>
                    <th>Priority</th><th>Deps</th><th>Regression</th><th style="width:40px"></th>
                </tr></thead>
                <tbody>
                    ${list.map(tc => {
                        const depCount = (tc.blocked_by_count || 0) + (tc.blocks_count || 0);
                        const depBadge = depCount > 0
                            ? `<span class="badge" style="background:${tc.blocked_by_count > 0 ? '#c4314b' : '#e9730c'};color:#fff" title="${tc.blocked_by_count || 0} blocked by, ${tc.blocks_count || 0} blocks">${depCount}</span>`
                            : '-';
                        return `<tr onclick="TestPlanningView.showCaseDetail(${tc.id})" style="cursor:pointer" class="clickable-row">
                        <td><span style="font-family:'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;font-weight:500;color:#1e3a5f;letter-spacing:-0.2px">${tc.code || '-'}</span></td>
                        <td>${tc.title}</td>
                        <td>${layerBadge(tc.test_layer)}</td>
                        <td>${tc.module || '-'}</td>
                        <td>${statusBadge(tc.status)}</td>
                        <td>${tc.priority}</td>
                        <td>${depBadge}</td>
                        <td>${tc.is_regression ? '✅' : '-'}</td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();TestPlanningView.deleteCase(${tc.id})">🗑</button>
                        </td>
                    </tr>`}).join('')}
                </tbody>
            </table>`;
    }

    async function showCaseModal(tc = null) {
        const pid = TestingShared.pid;
        const isEdit = !!tc;
        _activeCaseId = isEdit ? tc.id : null;
        _derivedTraceability = null;
        const title = isEdit ? 'Edit Test Case' : 'New Test Case';
        const members = await TeamMemberPicker.fetchMembers(pid);
        const assignedHtml = TeamMemberPicker.renderSelect('tcAssigned', members, isEdit ? (tc.assigned_to_id || tc.assigned_to || '') : '', { cssClass: 'form-control' });
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body" style="max-height:75vh;overflow-y:auto">
                ${isEdit ? `
                <div style="display:flex;gap:4px;margin-bottom:12px;border-bottom:1px solid #e0e0e0;padding-bottom:8px">
                    <button class="btn btn-sm case-tab-btn active" data-ctab="caseForm" onclick="TestPlanningView._switchCaseTab('caseForm')">📝 Details</button>
                    <button class="btn btn-sm case-tab-btn" data-ctab="casePerf" onclick="TestPlanningView._switchCaseTab('casePerf')">⚡ Performance</button>
                    <button class="btn btn-sm case-tab-btn" data-ctab="caseDeps" onclick="TestPlanningView._switchCaseTab('caseDeps')">🔗 Dependencies</button>
                </div>` : ''}

                <div id="casePanelForm" class="case-tab-panel">
                    <div style="display:flex;gap:8px;margin-bottom:12px">
                        <button type="button" class="btn btn-sm case-wizard-btn active" data-cwstep="1" onclick="TestPlanningView.switchCaseWizard(1)">1) Basics</button>
                        <button type="button" class="btn btn-sm case-wizard-btn" data-cwstep="2" onclick="TestPlanningView.switchCaseWizard(2)">2) Scope</button>
                    </div>

                    <div id="caseWizardStep1">
                        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:10px;margin-bottom:10px;background:#fff">
                            <div style="font-size:12px;font-weight:700;color:#334155;margin-bottom:8px">SECTION 1 — HEADER (Identity & Classification)</div>
                            <div class="form-row">
                                <div class="form-group"><label>Test Case Code *</label>
                                    <input id="tcCode" class="form-control" value="${isEdit ? (tc.code || '') : ''}" placeholder="e.g. TC-SD-0012"></div>
                                <div class="form-group"><label>Title *</label>
                                    <input id="tcTitle" class="form-control" value="${isEdit ? tc.title : ''}"></div>
                            </div>
                            <div class="form-row">
                                <div class="form-group"><label>Level *</label>
                                    <select id="tcLayer" class="form-control">
                                        ${['unit','sit','uat','e2e','regression','performance','cutover_rehearsal'].map(l =>
                                            `<option value="${l}" ${(isEdit && tc.test_layer === l) ? 'selected' : ''}>${l.toUpperCase()}</option>`).join('')}
                                    </select></div>
                                <div class="form-group"><label>Type</label>
                                    <select id="tcType" class="form-control">
                                        ${['functional','integration','e2e','regression','performance','security','data'].map(t =>
                                            `<option value="${t}" ${(isEdit && tc.test_type === t) ? 'selected' : ''}>${t}</option>`).join('')}
                                    </select></div>
                                <div class="form-group"><label>Module *</label>
                                    <input id="tcModule" class="form-control" value="${isEdit ? (tc.module || '') : ''}" placeholder="FI, MM, SD..."></div>
                                <div class="form-group"><label>Priority *</label>
                                    <select id="tcPriority" class="form-control">
                                        ${['low','medium','high','critical'].map(p =>
                                            `<option value="${p}" ${(isEdit && tc.priority === p) ? 'selected' : ''}>${p}</option>`).join('')}
                                    </select></div>
                                <div class="form-group"><label>Risk *</label>
                                    <select id="tcRisk" class="form-control">
                                        ${['low','medium','high','critical'].map(r =>
                                            `<option value="${r}" ${(isEdit && (tc.risk || 'medium') === r) ? 'selected' : ''}>${r}</option>`).join('')}
                                    </select></div>
                                <div class="form-group"><label>Status</label>
                                    <select id="tcStatus" class="form-control">
                                        ${['draft','ready','approved','in_review','deprecated'].map(s =>
                                            `<option value="${s}" ${(isEdit && tc.status === s) ? 'selected' : ''}>${s}</option>`).join('')}
                                    </select></div>
                            </div>
                            <div class="form-row">
                                <div class="form-group"><label>Owner</label>
                                    ${assignedHtml}</div>
                                <div class="form-group"><label>Reviewer</label>
                                    <input id="tcReviewer" class="form-control" value="${isEdit ? (tc.reviewer || '') : ''}" placeholder="Reviewer name"></div>
                                <div class="form-group"><label>Created Date</label>
                                    <input class="form-control" value="${isEdit ? ((tc.created_at || '').slice(0, 10) || '') : (new Date().toISOString().slice(0,10))}" disabled></div>
                                <div class="form-group"><label>Version</label>
                                    <input id="tcVersion" class="form-control" value="${isEdit ? (tc.version || '1.0') : '1.0'}"></div>
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group"><label>Suites</label>
                                <select id="tcSuiteId" class="form-control" multiple size="4"></select>
                                <div id="tcSuiteChips" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px"></div>
                            </div>
                        </div>

                        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:10px;margin-bottom:10px;background:#fff">
                            <div style="font-size:12px;font-weight:700;color:#334155;margin-bottom:8px">SECTION 3 — TEST LOGIC</div>
                        <div class="form-group"><label>Description</label>
                            <textarea id="tcDesc" class="form-control" rows="2">${isEdit ? (tc.description || '') : ''}</textarea></div>
                        <div class="form-group"><label>Preconditions *</label>
                            <textarea id="tcPrecond" class="form-control" rows="2">${isEdit ? (tc.preconditions || '') : ''}</textarea></div>

                        <div class="form-group">
                            <label style="display:flex;justify-content:space-between;align-items:center">
                                <span>Test Steps</span>
                                ${isEdit ? `<button class="btn btn-sm btn-primary" type="button" onclick="TestPlanningView.addStepRow()">+ Add Step</button>` : ''}
                            </label>
                            ${isEdit ? `
                            <div id="stepsContainer" style="margin-top:8px">
                                <div style="text-align:center;padding:12px"><div class="spinner"></div> Loading steps...</div>
                            </div>` : `
                            <div id="draftStepsContainer" style="margin-top:8px"></div>
                            <button type="button" class="btn btn-sm" onclick="TestPlanningView.addDraftStepRow()">+ Add Step</button>
                            `}
                        </div>

                        <div class="form-group"><label>Expected Result</label>
                            <textarea id="tcExpected" class="form-control" rows="2">${isEdit ? (tc.expected_result || '') : ''}</textarea></div>
                        </div>

                        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:10px;background:#fff">
                            <div style="font-size:12px;font-weight:700;color:#334155;margin-bottom:8px">SECTION 4 — DATA & DEPENDENCIES</div>
                        <div class="form-group"><label>Linked Data Set</label>
                            <input id="tcData" class="form-control" value="${isEdit ? (tc.test_data_set || '') : ''}"></div>
                        <div class="form-group"><label>Data Readiness Notes (required for SIT if no dataset)</label>
                            <textarea id="tcDataReadiness" class="form-control" rows="2">${isEdit ? (tc.data_readiness || '') : ''}</textarea></div>
                        <div class="form-row">
                            <div class="form-group"><label>
                                <input type="checkbox" id="tcRegression" ${isEdit && tc.is_regression ? 'checked' : ''}> Regression Set</label></div>
                        </div>
                        </div>

                        <div style="display:flex;justify-content:flex-end">
                            <button type="button" class="btn btn-primary btn-sm" onclick="TestPlanningView.switchCaseWizard(2)">Next: Scope</button>
                        </div>
                    </div>

                    <div id="caseWizardStep2" style="display:none">
                        <div style="font-size:12px;font-weight:700;color:#334155;margin-bottom:8px">SECTION 2 — COVERAGE (MASTER BLOCK)</div>
                        <div id="tcTraceRuleHint" style="font-size:12px;color:#c4314b;margin:0 0 10px 0">
                            For UNIT/SIT/UAT, at least one L3 basket is required.
                        </div>
                        <div style="border:1px solid #e0ddd8;border-radius:8px;padding:14px 16px;background:#FDFCFA">
                            <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px">
                                <span style="font-size:15px">🔗</span>
                                <strong style="font-size:13px;color:#0B1623">Scope Selection</strong>
                                <span style="font-size:11px;color:#999;margin-left:auto">Choose L3 first, then configure linked items</span>
                            </div>
                            <div class="form-row">
                                <div class="form-group"><label>L1 Value Chain</label>
                                    <select id="traceL1" class="form-control"><option value="">— Select L1 —</option></select>
                                </div>
                                <div class="form-group"><label>L2 Process Area</label>
                                    <select id="traceL2" class="form-control" disabled><option value="">— Select L2 —</option></select>
                                </div>
                                <div class="form-group"><label id="tcL3Label">L3 Process *</label>
                                    <select id="traceL3" class="form-control" disabled><option value="">— Select L3 —</option></select>
                                </div>
                            </div>
                            <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">
                                <button type="button" class="btn btn-sm btn-primary" id="traceAddL3Btn">+ Add L3 Scope</button>
                                <button type="button" class="btn btn-sm" id="traceClearAllBtn">Clear All</button>
                            </div>

                            <div id="traceBasket" style="display:flex;flex-direction:column;gap:8px"></div>
                            <div id="traceGroupDetail" style="margin-top:10px"></div>

                            <div id="derivedTraceabilityBox" style="margin-top:10px;border:1px solid #e5e7eb;border-radius:8px;padding:10px;background:#fff"></div>
                        </div>

                        <div style="margin-top:10px;border:1px solid #e5e7eb;border-radius:8px;padding:10px;background:#fff">
                            <div style="font-size:12px;font-weight:700;color:#334155;margin-bottom:8px">SECTION 5 — GOVERNANCE & IMPACT</div>
                            <div id="governanceImpactBox" style="font-size:12px;color:#334155"></div>
                        </div>

                        <div style="margin-top:10px;border:1px solid #e5e7eb;border-radius:8px;padding:10px;background:#fff">
                            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px">
                                <div style="font-size:12px;font-weight:700;color:#334155">SECTION 6 — L3 COVERAGE SNAPSHOT</div>
                                <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
                                    <select id="l3CoverageSelect" class="form-control" style="min-width:260px" onchange="TestPlanningView.onL3CoverageSelect(this.value)">
                                        <option value="">— Select L3 from basket —</option>
                                    </select>
                                    <button type="button" class="btn btn-sm" onclick="TestPlanningView.refreshL3Coverage(true)">Refresh</button>
                                </div>
                            </div>
                            <div id="l3CoverageBox" style="font-size:12px;color:#334155"></div>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-top:10px">
                            <button type="button" class="btn btn-sm" onclick="TestPlanningView.switchCaseWizard(1)">Back to Basics</button>
                            <button type="button" class="btn btn-primary btn-sm" onclick="TestPlanningView.saveCase(${isEdit ? tc.id : 'null'})">${isEdit ? 'Update Test Case' : 'Create Test Case'}</button>
                        </div>
                    </div>
                </div><!-- end casePanelForm -->

                ${isEdit ? `
                <!-- PERFORMANCE TAB -->
                <div id="casePanelPerf" class="case-tab-panel" style="display:none">
                    <div id="perfResultsContent"><div class="spinner" style="margin:16px auto"></div></div>
                    <div style="margin-top:12px"><canvas id="chartPerfTrend" height="200"></canvas></div>
                    <div style="border-top:1px solid #e0e0e0;margin-top:12px;padding-top:12px">
                        <h4>Add Performance Result</h4>
                        <div class="form-row">
                            <div class="form-group"><label>Response Time (ms) *</label>
                                <input id="perfResponseTime" class="form-control" type="number" placeholder="e.g. 250"></div>
                            <div class="form-group"><label>Target (ms) *</label>
                                <input id="perfTarget" class="form-control" type="number" placeholder="e.g. 500"></div>
                            <div class="form-group"><label>Throughput (rps)</label>
                                <input id="perfThroughput" class="form-control" type="number" placeholder="e.g. 100"></div>
                        </div>
                        <div class="form-row">
                            <div class="form-group"><label>Concurrent Users</label>
                                <input id="perfUsers" class="form-control" type="number" placeholder="e.g. 50"></div>
                            <div class="form-group"><label>Environment</label>
                                <input id="perfEnv" class="form-control" placeholder="DEV/QAS/PRD"></div>
                        </div>
                        <div class="form-group"><label>Notes</label>
                            <input id="perfNotes" class="form-control" placeholder="Optional"></div>
                        <button class="btn btn-primary btn-sm" onclick="TestPlanningView.addPerfResult(${tc.id})">Add Result</button>
                    </div>
                </div>

                <!-- DEPENDENCIES TAB -->
                <div id="casePanelDeps" class="case-tab-panel" style="display:none">
                    <div id="caseDepsContent"><div class="spinner" style="margin:16px auto"></div></div>
                    <div style="border-top:1px solid #e0e0e0;margin-top:12px;padding-top:12px">
                        <h4>Add Dependency</h4>
                        <div class="form-row">
                            <div class="form-group"><label>Other Case ID *</label>
                                <input id="depOtherCaseId" class="form-control" type="number" placeholder="Test case ID"></div>
                            <div class="form-group"><label>Direction</label>
                                <select id="depDirection" class="form-control">
                                    <option value="blocked_by">Blocked By</option>
                                    <option value="blocks">Blocks</option>
                                </select></div>
                            <div class="form-group"><label>Type</label>
                                <select id="depType" class="form-control">
                                    <option value="blocks">Blocks</option>
                                    <option value="related">Related</option>
                                    <option value="data_feeds">Data Feeds</option>
                                </select></div>
                        </div>
                        <button class="btn btn-primary btn-sm" onclick="TestPlanningView.addCaseDependency(${tc.id})">Add Dependency</button>
                    </div>
                </div>
                ` : ''}
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanningView.saveCase(${isEdit ? tc.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `;
        overlay.classList.add('open');

        // Load suite options
        const selectedSuiteIds = isEdit
            ? ((tc.suite_ids && tc.suite_ids.length)
                ? tc.suite_ids
                : [])
            : [];
        _loadSuiteOptions(selectedSuiteIds);

        // Initialize hierarchical traceability picker/basket
        await _initTraceabilityState(tc || null);
        await _initTraceabilityUI();

        // Layer-based requirement UX (ADR-008)
        const layerEl = document.getElementById('tcLayer');
        if (layerEl) {
            layerEl.addEventListener('change', _updateTraceabilityRequirementUI);
        }
        _updateTraceabilityRequirementUI();
        switchCaseWizard(1);

        if (!isEdit) {
            _draftSteps = [{ step_no: 1, action: '', expected_result: '' }];
            _renderDraftSteps();
        }

        // Load structured steps for existing cases
        if (isEdit) {
            _loadSteps(tc.id);
            _loadPerfResults(tc.id);
            _loadCaseDependencies(tc.id);
        }
    }

    async function _loadSuiteOptions(selectedSuiteIds) {
        const pid = TestingShared.pid;
        try {
            const res = await API.get(`/programs/${pid}/testing/suites?per_page=200`);
            const suites = res.items || res || [];
            const sel = document.getElementById('tcSuiteId');
            if (!sel) return;
            sel.innerHTML = '';
            suites.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = `${s.name} (${s.purpose || s.suite_type || 'Custom'})`;
                if ((selectedSuiteIds || []).map(Number).includes(Number(s.id))) opt.selected = true;
                sel.appendChild(opt);
            });
            sel.onchange = _renderSuiteChips;
            _renderSuiteChips();
        } catch (e) {
            console.warn('Could not load suites for selector:', e);
        }
    }

    function _renderSuiteChips() {
        const sel = document.getElementById('tcSuiteId');
        const chips = document.getElementById('tcSuiteChips');
        if (!sel || !chips) return;
        const selected = Array.from(sel.selectedOptions || []);
        if (!selected.length) {
            chips.innerHTML = '<span style="font-size:12px;color:#777">No suite selected</span>';
            return;
        }
        chips.innerHTML = selected.map(opt =>
            `<span class="badge" style="background:#e8f1ff;color:#1f3d7a;border:1px solid #bfd6ff;padding:3px 8px">
                ${esc(opt.textContent)}
             </span>`
        ).join('');
    }

    // ── ADR-008 B: Hierarchical Traceability Picker + Basket ───────────
    function _toNum(val) {
        const n = parseInt(val, 10);
        return Number.isFinite(n) ? n : null;
    }

    function _listUnique(values) {
        return Array.from(new Set((values || []).filter(v => v !== null && v !== undefined && v !== '')));
    }

    function _traceRequirementL3(req) {
        return String(req?.scope_item_id || req?.process_level_id || '').trim();
    }

    function _traceBacklogL3(item) {
        const reqId = item?.explore_requirement_id;
        const req = _traceabilityOptions.requirements.find(r => String(r.id) === String(reqId));
        return _traceRequirementL3(req);
    }

    function _traceConfigL3(item) {
        const reqId = item?.explore_requirement_id;
        const req = _traceabilityOptions.requirements.find(r => String(r.id) === String(reqId));
        return _traceRequirementL3(req);
    }

    function _findProcess(id) {
        return _traceabilityOptions.processLevels.find(p => String(p.id) === String(id));
    }

    function _processLabel(id) {
        const p = _findProcess(id);
        if (!p) return String(id);
        return `${p.code || ''} — ${p.name || ''}`.trim();
    }

    function _requirementLabel(id) {
        const r = _traceabilityOptions.requirements.find(x => String(x.id) === String(id));
        return r ? `${r.code || 'REQ'} — ${r.title || ''}` : String(id);
    }

    function _backlogLabel(id) {
        const b = _traceabilityOptions.backlogItems.find(x => String(x.id) === String(id));
        return b ? `${b.code || 'BL'} — ${b.title || ''}` : String(id);
    }

    function _configLabel(id) {
        const c = _traceabilityOptions.configItems.find(x => String(x.id) === String(id));
        return c ? `${c.code || 'CFG'} — ${c.title || ''}` : String(id);
    }

    function _normalizeTraceGroups(groups) {
        const normalized = [];
        (groups || []).forEach(g => {
            const l3 = String(g.l3_process_level_id || g.l3_id || '').trim();
            if (!l3) return;
            normalized.push({
                l3_process_level_id: l3,
                l4_process_level_ids: _listUnique((g.l4_process_level_ids || []).map(String)),
                explore_requirement_ids: _listUnique((g.explore_requirement_ids || []).map(String)),
                backlog_item_ids: _listUnique((g.backlog_item_ids || []).map(_toNum).filter(Number.isFinite)),
                config_item_ids: _listUnique((g.config_item_ids || []).map(_toNum).filter(Number.isFinite)),
                manual_requirement_ids: _listUnique((g.manual_requirement_ids || []).map(String)),
                manual_backlog_item_ids: _listUnique((g.manual_backlog_item_ids || []).map(_toNum).filter(Number.isFinite)),
                manual_config_item_ids: _listUnique((g.manual_config_item_ids || []).map(_toNum).filter(Number.isFinite)),
                excluded_requirement_ids: _listUnique((g.excluded_requirement_ids || []).map(String)),
                excluded_backlog_item_ids: _listUnique((g.excluded_backlog_item_ids || []).map(_toNum).filter(Number.isFinite)),
                excluded_config_item_ids: _listUnique((g.excluded_config_item_ids || []).map(_toNum).filter(Number.isFinite)),
            });
        });

        const dedup = [];
        const seen = new Set();
        normalized.forEach(g => {
            if (seen.has(g.l3_process_level_id)) return;
            seen.add(g.l3_process_level_id);
            dedup.push(g);
        });
        return dedup;
    }

    async function _initTraceabilityState(tc) {
        const pid = TestingShared.pid;
        const [levelsRes, reqRes, backlogRes, configRes] = await Promise.all([
            API.get(`/explore/process-levels?project_id=${pid}&flat=true`).catch(() => []),
            API.get(`/explore/requirements?project_id=${pid}&per_page=1000`).catch(() => ({ items: [] })),
            API.get(`/programs/${pid}/backlog?per_page=1000`).catch(() => ({ items: [] })),
            API.get(`/programs/${pid}/config-items`).catch(() => []),
        ]);

        _traceabilityOptions.processLevels = Array.isArray(levelsRes) ? levelsRes : (levelsRes.items || []);
        _traceabilityOptions.requirements = reqRes.items || [];
        _traceabilityOptions.backlogItems = backlogRes.items || [];
        _traceabilityOptions.configItems = Array.isArray(configRes) ? configRes : (configRes.items || []);

        let groups = [];
        if (tc && Array.isArray(tc.traceability_links) && tc.traceability_links.length) {
            groups = tc.traceability_links.map(t => ({
                l3_process_level_id: t.l3_process_level_id,
                l4_process_level_ids: t.l4_process_level_ids || [],
                explore_requirement_ids: t.explore_requirement_ids || [],
                backlog_item_ids: t.backlog_item_ids || [],
                config_item_ids: t.config_item_ids || [],
                manual_requirement_ids: t.manual_requirement_ids || [],
                manual_backlog_item_ids: t.manual_backlog_item_ids || [],
                manual_config_item_ids: t.manual_config_item_ids || [],
                excluded_requirement_ids: t.excluded_requirement_ids || [],
                excluded_backlog_item_ids: t.excluded_backlog_item_ids || [],
                excluded_config_item_ids: t.excluded_config_item_ids || [],
            }));
        } else if (tc && (tc.process_level_id || tc.explore_requirement_id || tc.backlog_item_id || tc.config_item_id)) {
            groups = [{
                l3_process_level_id: tc.process_level_id || '',
                l4_process_level_ids: [],
                explore_requirement_ids: tc.explore_requirement_id ? [tc.explore_requirement_id] : [],
                backlog_item_ids: tc.backlog_item_id ? [tc.backlog_item_id] : [],
                config_item_ids: tc.config_item_id ? [tc.config_item_id] : [],
                manual_requirement_ids: [],
                manual_backlog_item_ids: [],
                manual_config_item_ids: [],
                excluded_requirement_ids: [],
                excluded_backlog_item_ids: [],
                excluded_config_item_ids: [],
            }];
        }
        _traceabilityState = { groups: _normalizeTraceGroups(groups) };
    }

    function _fillSimpleSelect(el, options, placeholder) {
        if (!el) return;
        el.innerHTML = `<option value="">${placeholder}</option>`;
        options.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o.value;
            opt.textContent = o.label;
            el.appendChild(opt);
        });
    }

    function _processByLevel(level, parentId = null) {
        return (_traceabilityOptions.processLevels || []).filter(p => {
            if (Number(p.level) !== Number(level)) return false;
            if (parentId === null) return true;
            return String(p.parent_id || '') === String(parentId || '');
        });
    }

    async function _initTraceabilityUI() {
        const l1 = document.getElementById('traceL1');
        const l2 = document.getElementById('traceL2');
        const l3 = document.getElementById('traceL3');
        const addBtn = document.getElementById('traceAddL3Btn');
        const clearBtn = document.getElementById('traceClearAllBtn');

        const l1Items = _processByLevel(1).map(p => ({ value: p.id, label: `${p.code || ''} — ${p.name || ''}` }));
        _fillSimpleSelect(l1, l1Items, '— Select L1 —');

        const onL1Change = () => {
            const l2Items = _processByLevel(2, l1.value).map(p => ({ value: p.id, label: `${p.code || ''} — ${p.name || ''}` }));
            _fillSimpleSelect(l2, l2Items, '— Select L2 —');
            l2.disabled = !l1.value;
            _fillSimpleSelect(l3, [], '— Select L3 —');
            l3.disabled = true;
        };
        const onL2Change = () => {
            const l3Items = _processByLevel(3, l2.value).map(p => ({ value: p.id, label: `${p.code || ''} — ${p.name || ''}` }));
            _fillSimpleSelect(l3, l3Items, '— Select L3 —');
            l3.disabled = !l2.value;
        };

        l1?.addEventListener('change', onL1Change);
        l2?.addEventListener('change', onL2Change);
        addBtn?.addEventListener('click', () => {
            const selectedL3 = l3?.value;
            if (!selectedL3) return App.toast('Select L3 first', 'error');
            if (_traceabilityState.groups.some(g => String(g.l3_process_level_id) === String(selectedL3))) {
                return App.toast('This L3 basket already exists', 'error');
            }
            _traceabilityState.groups.push({
                l3_process_level_id: selectedL3,
                l4_process_level_ids: [],
                explore_requirement_ids: [],
                backlog_item_ids: [],
                config_item_ids: [],
                manual_requirement_ids: [],
                manual_backlog_item_ids: [],
                manual_config_item_ids: [],
                excluded_requirement_ids: [],
                excluded_backlog_item_ids: [],
                excluded_config_item_ids: [],
            });
            _renderTraceabilityBasket();
            _updateTraceabilityRequirementUI();
        });
        clearBtn?.addEventListener('click', clearTraceGroups);

        onL1Change();
        _renderTraceabilityBasket();
        _updateTraceabilityRequirementUI();
    }

    function _groupHasChildren(group) {
        return (group.l4_process_level_ids || []).length
            || (group.explore_requirement_ids || []).length
            || (group.backlog_item_ids || []).length
            || (group.config_item_ids || []).length;
    }

    function _renderTraceabilityBasket() {
        const basket = document.getElementById('traceBasket');
        const detail = document.getElementById('traceGroupDetail');
        if (!basket) return;
        const groups = _traceabilityState.groups || [];
        if (!groups.length) {
            basket.innerHTML = '<div style="font-size:12px;color:#777">No L3 scopes selected yet.</div>';
            if (detail) detail.innerHTML = '';
            _renderDerivedTraceability();
            _renderGovernanceImpact();
            _renderL3CoveragePanel();
            _refreshDerivedTraceabilityFromApi();
            return;
        }

        basket.innerHTML = groups.map((g, idx) => {
            const l3Options = _processByLevel(3).map(p => `<option value="${p.id}" ${String(p.id) === String(g.l3_process_level_id) ? 'selected' : ''}>${esc(`${p.code || ''} — ${p.name || ''}`)}</option>`).join('');
            return `
                <div style="border:1px solid ${_activeTraceGroupIndex === idx ? '#9ec8ff' : '#e5e7eb'};border-radius:8px;padding:8px;background:#fff">
                    <div style="display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap">
                        <div style="display:flex;gap:8px;align-items:center;min-width:260px;flex:1">
                            <span class="badge" style="background:#0a6ed1;color:#fff">L3</span>
                            <select class="form-control" style="max-width:340px" onchange="TestPlanningView.changeTraceGroupL3(${idx}, this.value)">
                                ${l3Options}
                            </select>
                        </div>
                        <div style="display:flex;gap:6px;align-items:center">
                            <span style="font-size:12px;color:#555">L4:${(g.l4_process_level_ids || []).length} · Req:${(g.explore_requirement_ids || []).length} · WRICEF:${(g.backlog_item_ids || []).length} · Config:${(g.config_item_ids || []).length}</span>
                            <button type="button" class="btn btn-sm" onclick="TestPlanningView.openTraceGroupDetail(${idx})">Configure Details</button>
                            <button type="button" class="btn btn-sm btn-danger" onclick="TestPlanningView.removeTraceGroup(${idx})">Remove</button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        if (detail) {
            if (_activeTraceGroupIndex === null || !_traceabilityState.groups[_activeTraceGroupIndex]) {
                detail.innerHTML = '';
            } else {
                detail.innerHTML = _renderTraceGroupDetailDrawer(_activeTraceGroupIndex);
            }
        }
        _renderDerivedTraceability();
        _renderGovernanceImpact();
        _renderL3CoveragePanel();
        _refreshDerivedTraceabilityFromApi();
    }

    function _renderL3CoveragePanel() {
        const sel = document.getElementById('l3CoverageSelect');
        const box = document.getElementById('l3CoverageBox');
        if (!box) return;

        const groups = _traceabilityState.groups || [];
        const l3Ids = _listUnique(groups.map(g => String(g.l3_process_level_id || '')).filter(Boolean));

        if (sel) {
            const current = _l3CoverageState.selectedL3;
            sel.innerHTML = `<option value="">— Select L3 from basket —</option>${l3Ids.map(l3Id =>
                `<option value="${esc(l3Id)}" ${(String(current || '') === String(l3Id)) ? 'selected' : ''}>${esc(_processLabel(l3Id))}</option>`
            ).join('')}`;
        }

        if (!l3Ids.length) {
            _l3CoverageState.selectedL3 = null;
            box.innerHTML = '<span style="color:#777">Add at least one L3 basket to see scope coverage.</span>';
            return;
        }

        if (!_l3CoverageState.selectedL3 || !l3Ids.includes(String(_l3CoverageState.selectedL3))) {
            _l3CoverageState.selectedL3 = l3Ids[0];
            if (sel) sel.value = _l3CoverageState.selectedL3;
        }

        const cached = _l3CoverageState.cache[String(_l3CoverageState.selectedL3)];
        if (cached) {
            _renderL3CoverageData(cached);
            return;
        }

        box.innerHTML = '<span style="color:#777">Select refresh to load L3 coverage snapshot.</span>';
    }

    function _renderL3CoverageData(data) {
        const box = document.getElementById('l3CoverageBox');
        if (!box) return;
        const summary = data?.summary || {};
        const l3 = data?.l3 || {};
        const passRate = Number(summary.pass_rate || 0);
        const ready = String(summary.readiness || 'not_ready') === 'ready';
        const readinessColor = ready ? '#107e3e' : '#c4314b';

        const processSteps = data?.process_steps || [];
        const reqs = data?.requirements || [];
        const ifaces = data?.interfaces || [];

        box.innerHTML = `
            <div style="margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
                <div><strong>${esc(l3.code || '')}</strong> ${esc(l3.name || '')}</div>
                <span class="badge" style="background:${readinessColor};color:#fff">${ready ? 'Ready' : 'Not Ready'}</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:8px;margin-bottom:8px">
                <div><div style="color:#64748b">Total TCs</div><div><strong>${summary.total_test_cases || 0}</strong></div></div>
                <div><div style="color:#64748b">Pass Rate</div><div><strong style="color:${readinessColor}">${passRate.toFixed(1)}%</strong></div></div>
                <div><div style="color:#64748b">Step Coverage</div><div><strong>${esc(summary.process_step_coverage || '0/0')}</strong></div></div>
                <div><div style="color:#64748b">Req Coverage</div><div><strong>${esc(summary.requirement_coverage || '0/0')}</strong></div></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
                <div style="padding:8px;border:1px solid #e2e8f0;border-radius:6px;background:#fff">Process Steps: <strong>${processSteps.length}</strong></div>
                <div style="padding:8px;border:1px solid #e2e8f0;border-radius:6px;background:#fff">Requirements: <strong>${reqs.length}</strong></div>
                <div style="padding:8px;border:1px solid #e2e8f0;border-radius:6px;background:#fff">Interfaces: <strong>${ifaces.length}</strong></div>
            </div>
        `;
    }

    async function refreshL3Coverage(force = false) {
        const pid = TestingShared.pid;
        const l3Id = _l3CoverageState.selectedL3 || document.getElementById('l3CoverageSelect')?.value;
        const box = document.getElementById('l3CoverageBox');

        if (!pid || !l3Id) {
            if (box) box.innerHTML = '<span style="color:#777">Select an L3 scope to load coverage.</span>';
            return;
        }

        if (!force && _l3CoverageState.cache[String(l3Id)]) {
            _renderL3CoverageData(_l3CoverageState.cache[String(l3Id)]);
            return;
        }

        if (box) box.innerHTML = '<span style="color:#777">Loading coverage…</span>';
        try {
            const data = await API.get(`/programs/${pid}/testing/scope-coverage/${l3Id}`);
            _l3CoverageState.cache[String(l3Id)] = data;
            _l3CoverageState.selectedL3 = String(l3Id);
            _renderL3CoverageData(data);
        } catch (e) {
            if (box) box.innerHTML = `<span style="color:#c4314b">Coverage load failed: ${esc(e.message || 'Unknown error')}</span>`;
        }
    }

    function onL3CoverageSelect(l3Id) {
        _l3CoverageState.selectedL3 = l3Id ? String(l3Id) : null;
        refreshL3Coverage(false);
    }

    async function _refreshDerivedTraceabilityFromApi() {
        if (!_activeCaseId) return;
        try {
            _derivedTraceability = await API.get(`/testing/catalog/${_activeCaseId}/traceability-derived`);
            _renderDerivedTraceability();
            _renderGovernanceImpact();
        } catch (e) {
            // Keep local fallback if API unavailable
        }
    }

    function _renderDerivedTraceability() {
        const box = document.getElementById('derivedTraceabilityBox');
        if (!box) return;

        if (_derivedTraceability && Array.isArray(_derivedTraceability.groups)) {
            const summary = _derivedTraceability.summary || {};
            const allGroups = _derivedTraceability.groups;
            const reqCount = allGroups.reduce((n, g) => n + (g.summary?.derived_requirements || 0), 0);
            const wricefCount = allGroups.reduce((n, g) => n + (g.summary?.derived_wricef || 0), 0);
            const cfgCount = allGroups.reduce((n, g) => n + (g.summary?.derived_config_items || 0), 0);
            const manualCount = allGroups.reduce((n, g) => n + (g.summary?.manual_additions || 0), 0);
            const notCovered = summary.not_covered_total || 0;

            box.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
                    <div style="font-weight:600">Derived Traceability (Auto-generated)</div>
                    <div style="display:flex;gap:6px;align-items:center;font-size:11px">
                        <span class="badge" style="background:#0a6ed1;color:#fff">Derived (readonly)</span>
                        <span class="badge" style="background:#e5a800;color:#111">Manually Added</span>
                        <span class="badge" style="background:#c4314b;color:#fff">Not Covered in Test</span>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:12px">
                    <div><strong>Requirements (${reqCount})</strong></div>
                    <div><strong>WRICEF (${wricefCount})</strong></div>
                    <div><strong>Config Items (${cfgCount})</strong></div>
                </div>
                <div style="margin-top:8px;font-size:12px;color:#334155">
                    Manual additions: <strong>${manualCount}</strong> · Not covered: <strong style="color:${notCovered ? '#c4314b' : '#107e3e'}">${notCovered}</strong>
                </div>
            `;
            return;
        }

        const groups = _traceabilityState.groups || [];
        if (!groups.length) {
            box.innerHTML = `
                <div style="font-weight:600;margin-bottom:6px">Derived Traceability (Auto-generated)</div>
                <div style="color:#777">No derived items yet. Add at least one L3 scope.</div>`;
            return;
        }

        const selectedL3 = new Set(groups.map(g => String(g.l3_process_level_id)));
        const reqs = (_traceabilityOptions.requirements || []).filter(r => {
            const l3id = _traceRequirementL3(r);
            return l3id && selectedL3.has(String(l3id));
        });
        const reqIds = new Set(reqs.map(r => String(r.id)));
        const wricef = (_traceabilityOptions.backlogItems || []).filter(b => reqIds.has(String(b.explore_requirement_id || '')));
        const cfg = (_traceabilityOptions.configItems || []).filter(c => reqIds.has(String(c.explore_requirement_id || '')));

        const fit = reqs.filter(r => String(r.fit_status || '').toLowerCase() === 'fit').length;
        const gap = reqs.filter(r => String(r.fit_status || '').toLowerCase() === 'gap').length;
        const partial = reqs.filter(r => String(r.fit_status || '').toLowerCase().includes('partial')).length;

        const iface = wricef.filter(w => String(w.wricef_type || '').toLowerCase() === 'interface').length;
        const enh = wricef.filter(w => String(w.wricef_type || '').toLowerCase() === 'enhancement').length;
        const rep = wricef.filter(w => String(w.wricef_type || '').toLowerCase() === 'report').length;

        box.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
                <div style="font-weight:600">Derived Traceability (Auto-generated)</div>
                <div style="display:flex;gap:6px;align-items:center;font-size:11px">
                    <span class="badge" style="background:#0a6ed1;color:#fff">Derived (readonly)</span>
                    <span class="badge" style="background:#e5a800;color:#111">Manually Added</span>
                    <span class="badge" style="background:#c4314b;color:#fff">Not Covered in Test</span>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:12px">
                <div><strong>Requirements (${reqs.length})</strong><br><span style="color:#666">${gap} Gap | ${partial} Partial Fit | ${fit} Fit</span></div>
                <div><strong>WRICEF (${wricef.length})</strong><br><span style="color:#666">${iface} Interface | ${enh} Enhancement | ${rep} Report</span></div>
                <div><strong>Config Items (${cfg.length})</strong><br><span style="color:#666">${cfg.slice(0,2).map(c => esc(c.title || c.code || 'Item')).join(' · ') || '—'}</span></div>
            </div>
        `;
    }

    function _renderGovernanceImpact() {
        const box = document.getElementById('governanceImpactBox');
        if (!box) return;
        const groups = _traceabilityState.groups || [];
        const coverageBase = groups.length ? 100 : 0;
        const readiness = groups.length ? 'in_progress' : 'not_started';
        const notCovered = _derivedTraceability?.summary?.not_covered_total || 0;
        box.innerHTML = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
                <div><strong>Impacted L3 Readiness %</strong><br><span>${coverageBase}% (scope-linked)</span></div>
                <div><strong>Historical Pass Rate</strong><br><span>Derived from executions after save</span></div>
                <div><strong>Linked Defects</strong><br><span>Summary available after execution cycles</span></div>
                <div><strong>Coverage Gaps Warning</strong><br><span style="color:${groups.length ? (notCovered ? '#c4314b' : '#107e3e') : '#c4314b'}">${groups.length ? (notCovered ? `${notCovered} item(s) not covered` : 'No uncovered derived item') : 'No L3 scope selected'}</span></div>
            </div>
            <div style="margin-top:8px;color:#475569">Status: ${readiness}</div>
        `;
    }

    function _renderTraceGroupDetailDrawer(index) {
        const g = _traceabilityState.groups[index];
        if (!g) return '';
        const derivedGroup = (_derivedTraceability?.groups || []).find(x => String(x.l3_process_level_id) === String(g.l3_process_level_id));

        const l4Options = _processByLevel(4, g.l3_process_level_id)
            .filter(p => !(g.l4_process_level_ids || []).map(String).includes(String(p.id)))
            .map(p => `<option value="${p.id}">${esc(`${p.code || ''} — ${p.name || ''}`)}</option>`).join('');
        const reqOptions = (_traceabilityOptions.requirements || [])
            .filter(r => {
                const l3id = _traceRequirementL3(r);
                return !l3id || String(l3id) === String(g.l3_process_level_id);
            })
            .filter(r => !(g.explore_requirement_ids || []).map(String).includes(String(r.id)))
            .map(r => `<option value="${r.id}">${esc(`${r.code || 'REQ'} — ${r.title || ''}`)}</option>`).join('');
        const wricefOptions = (_traceabilityOptions.backlogItems || [])
            .filter(b => {
                const l3id = _traceBacklogL3(b);
                return !l3id || String(l3id) === String(g.l3_process_level_id);
            })
            .filter(b => !(g.backlog_item_ids || []).map(Number).includes(Number(b.id)))
            .map(b => `<option value="${b.id}">${esc(`${b.code || 'BL'} — ${b.title || ''}`)}</option>`).join('');
        const cfgOptions = (_traceabilityOptions.configItems || [])
            .filter(c => {
                const l3id = _traceConfigL3(c);
                return !l3id || String(l3id) === String(g.l3_process_level_id);
            })
            .filter(c => !(g.config_item_ids || []).map(Number).includes(Number(c.id)))
            .map(c => `<option value="${c.id}">${esc(`${c.code || 'CFG'} — ${c.title || ''}`)}</option>`).join('');

        const manualReqOptions = (_traceabilityOptions.requirements || [])
            .filter(r => {
                const l3id = _traceRequirementL3(r);
                return !l3id || String(l3id) === String(g.l3_process_level_id);
            })
            .filter(r => !(g.manual_requirement_ids || []).map(String).includes(String(r.id)))
            .map(r => `<option value="${r.id}">${esc(`${r.code || 'REQ'} — ${r.title || ''}`)}</option>`).join('');
        const manualWricefOptions = (_traceabilityOptions.backlogItems || [])
            .filter(b => {
                const l3id = _traceBacklogL3(b);
                return !l3id || String(l3id) === String(g.l3_process_level_id);
            })
            .filter(b => !(g.manual_backlog_item_ids || []).map(Number).includes(Number(b.id)))
            .map(b => `<option value="${b.id}">${esc(`${b.code || 'BL'} — ${b.title || ''}`)}</option>`).join('');
        const manualCfgOptions = (_traceabilityOptions.configItems || [])
            .filter(c => {
                const l3id = _traceConfigL3(c);
                return !l3id || String(l3id) === String(g.l3_process_level_id);
            })
            .filter(c => !(g.manual_config_item_ids || []).map(Number).includes(Number(c.id)))
            .map(c => `<option value="${c.id}">${esc(`${c.code || 'CFG'} — ${c.title || ''}`)}</option>`).join('');

        const renderTags = (title, items, type, labelFn) => `
            <div style="margin-top:8px">
                <div style="font-size:12px;color:#555;margin-bottom:4px">${title}</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px">
                    ${(items || []).length
                        ? (items || []).map(v => `<span class="badge" style="background:#e8f1ff;color:#1f3d7a;border:1px solid #bfd6ff;padding:3px 8px">${esc(labelFn(v))} <button type="button" style="margin-left:6px;border:none;background:transparent;color:#1f3d7a;cursor:pointer" onclick="TestPlanningView.removeTraceChild(${index}, '${type}', '${String(v)}')">×</button></span>`).join('')
                        : '<span style="font-size:12px;color:#999">None</span>'}
                </div>
            </div>`;

        const renderManualTags = (title, items, type, labelFn) => `
            <div style="margin-top:8px">
                <div style="font-size:12px;color:#555;margin-bottom:4px">${title}</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px">
                    ${(items || []).length
                        ? (items || []).map(v => `<span class="badge" style="background:#fff7e6;color:#7a5100;border:1px solid #f5d48b;padding:3px 8px">${esc(labelFn(v))} <button type="button" style="margin-left:6px;border:none;background:transparent;color:#7a5100;cursor:pointer" onclick="TestPlanningView.removeTraceManual(${index}, '${type}', '${String(v)}')">×</button></span>`).join('')
                        : '<span style="font-size:12px;color:#999">None</span>'}
                </div>
            </div>`;

        const renderDerivedRows = (title, items, excludedIds, type, labelFn) => `
            <div style="margin-top:8px">
                <div style="font-size:12px;color:#555;margin-bottom:4px">${title}</div>
                ${(items || []).length ? `
                    <div style="display:flex;flex-direction:column;gap:4px;max-height:120px;overflow:auto;border:1px solid #e2e8f0;border-radius:6px;padding:6px;background:#fff">
                        ${(items || []).map(item => {
                            const itemId = String(item.id);
                            const checked = (excludedIds || []).map(String).includes(itemId);
                            return `<label style="font-size:12px;color:#334155;display:flex;align-items:center;gap:6px">
                                <input type="checkbox" ${checked ? 'checked' : ''} onchange="TestPlanningView.toggleTraceExcluded(${index}, '${type}', '${itemId}', this.checked)">
                                <span>${esc(labelFn(item.id))}</span>
                                <span style="margin-left:auto;color:${item.coverage_status === 'not_covered' ? '#c4314b' : '#107e3e'}">${item.coverage_status === 'not_covered' ? 'Not Covered' : 'Covered'}</span>
                            </label>`;
                        }).join('')}
                    </div>
                ` : '<span style="font-size:12px;color:#999">No derived item</span>'}
            </div>`;

        return `
            <div style="border:1px solid #d7e7ff;border-radius:8px;padding:10px;background:#f7fbff">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <strong style="font-size:12px">Configure L3 Details: ${esc(_processLabel(g.l3_process_level_id))}</strong>
                    <button type="button" class="btn btn-sm" onclick="TestPlanningView.closeTraceGroupDetail()">Close</button>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
                    <div style="display:flex;gap:6px"><select id="traceGroup_${index}_l4" class="form-control"><option value="">— Add L4 —</option>${l4Options}</select><button type="button" class="btn btn-sm" onclick="TestPlanningView.addTraceChild(${index}, 'l4')">Add</button></div>
                    <div style="display:flex;gap:6px"><select id="traceGroup_${index}_req" class="form-control"><option value="">— Add Requirement —</option>${reqOptions}</select><button type="button" class="btn btn-sm" onclick="TestPlanningView.addTraceChild(${index}, 'req')">Add</button></div>
                    <div style="display:flex;gap:6px"><select id="traceGroup_${index}_wricef" class="form-control"><option value="">— Add WRICEF —</option>${wricefOptions}</select><button type="button" class="btn btn-sm" onclick="TestPlanningView.addTraceChild(${index}, 'wricef')">Add</button></div>
                    <div style="display:flex;gap:6px"><select id="traceGroup_${index}_config" class="form-control"><option value="">— Add Config —</option>${cfgOptions}</select><button type="button" class="btn btn-sm" onclick="TestPlanningView.addTraceChild(${index}, 'config')">Add</button></div>
                </div>
                ${renderTags('L4', g.l4_process_level_ids, 'l4', _processLabel)}
                ${renderTags('Requirements', g.explore_requirement_ids, 'req', _requirementLabel)}
                ${renderTags('WRICEF', g.backlog_item_ids, 'wricef', _backlogLabel)}
                ${renderTags('Config', g.config_item_ids, 'config', _configLabel)}

                ${_activeCaseId ? `
                <div style="margin-top:10px;padding-top:10px;border-top:1px dashed #bfd6ff">
                    <div style="font-size:12px;font-weight:700;color:#334155;margin-bottom:6px">Governance Overrides</div>
                    <div style="font-size:11px;color:#64748b;margin-bottom:6px">Exclude derived items to mark not-covered, or add manual coverage items.</div>

                    ${renderDerivedRows('Exclude Derived Requirements', derivedGroup?.derived?.requirements || [], g.excluded_requirement_ids || [], 'req', _requirementLabel)}
                    ${renderDerivedRows('Exclude Derived WRICEF', derivedGroup?.derived?.wricef || [], g.excluded_backlog_item_ids || [], 'wricef', _backlogLabel)}
                    ${renderDerivedRows('Exclude Derived Config', derivedGroup?.derived?.config_items || [], g.excluded_config_item_ids || [], 'config', _configLabel)}

                    <div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
                        <div style="display:flex;gap:6px"><select id="traceGroup_${index}_manual_req" class="form-control"><option value="">— Add Manual Requirement —</option>${manualReqOptions}</select><button type="button" class="btn btn-sm" onclick="TestPlanningView.addTraceManual(${index}, 'req')">Add</button></div>
                        <div style="display:flex;gap:6px"><select id="traceGroup_${index}_manual_wricef" class="form-control"><option value="">— Add Manual WRICEF —</option>${manualWricefOptions}</select><button type="button" class="btn btn-sm" onclick="TestPlanningView.addTraceManual(${index}, 'wricef')">Add</button></div>
                        <div style="display:flex;gap:6px"><select id="traceGroup_${index}_manual_config" class="form-control"><option value="">— Add Manual Config —</option>${manualCfgOptions}</select><button type="button" class="btn btn-sm" onclick="TestPlanningView.addTraceManual(${index}, 'config')">Add</button></div>
                    </div>

                    ${renderManualTags('Manual Requirements', g.manual_requirement_ids || [], 'req', _requirementLabel)}
                    ${renderManualTags('Manual WRICEF', g.manual_backlog_item_ids || [], 'wricef', _backlogLabel)}
                    ${renderManualTags('Manual Config', g.manual_config_item_ids || [], 'config', _configLabel)}

                    <div style="display:flex;justify-content:flex-end;margin-top:10px">
                        <button type="button" class="btn btn-primary btn-sm" onclick="TestPlanningView.saveTraceOverrides()">Save Overrides</button>
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    }

    function clearTraceGroups() {
        if (!(_traceabilityState.groups || []).length) return;
        if (!confirm('Clear all selected L3 baskets and linked items?')) return;
        _traceabilityState.groups = [];
        _activeTraceGroupIndex = null;
        _renderTraceabilityBasket();
        _updateTraceabilityRequirementUI();
    }

    function removeTraceGroup(index) {
        const group = _traceabilityState.groups[index];
        if (!group) return;
        if (_groupHasChildren(group) && !confirm('This L3 has linked items. Remove and clear all linked selections?')) {
            return;
        }
        _traceabilityState.groups.splice(index, 1);
        if (_activeTraceGroupIndex === index) _activeTraceGroupIndex = null;
        if (_activeTraceGroupIndex !== null && _activeTraceGroupIndex > index) _activeTraceGroupIndex -= 1;
        _renderTraceabilityBasket();
        _updateTraceabilityRequirementUI();
    }

    function changeTraceGroupL3(index, newL3Id) {
        const group = _traceabilityState.groups[index];
        if (!group || !newL3Id || String(group.l3_process_level_id) === String(newL3Id)) return;
        if (_traceabilityState.groups.some((g, i) => i !== index && String(g.l3_process_level_id) === String(newL3Id))) {
            return App.toast('This L3 basket already exists', 'error');
        }
        if (_groupHasChildren(group) && !confirm('Changing L3 will clear linked L4/Requirement/WRICEF/Config items. Continue?')) {
            _renderTraceabilityBasket();
            return;
        }
        group.l3_process_level_id = newL3Id;
        group.l4_process_level_ids = [];
        group.explore_requirement_ids = [];
        group.backlog_item_ids = [];
        group.config_item_ids = [];
        group.manual_requirement_ids = [];
        group.manual_backlog_item_ids = [];
        group.manual_config_item_ids = [];
        group.excluded_requirement_ids = [];
        group.excluded_backlog_item_ids = [];
        group.excluded_config_item_ids = [];
        _activeTraceGroupIndex = index;
        _renderTraceabilityBasket();
    }

    function openTraceGroupDetail(index) {
        if (!_traceabilityState.groups[index]) return;
        _activeTraceGroupIndex = index;
        _renderTraceabilityBasket();
    }

    function closeTraceGroupDetail() {
        _activeTraceGroupIndex = null;
        _renderTraceabilityBasket();
    }

    function addTraceChild(index, type) {
        const group = _traceabilityState.groups[index];
        if (!group) return;
        const elId = `traceGroup_${index}_${type}`;
        const value = document.getElementById(elId)?.value;
        if (!value) return;

        if (type === 'l4') group.l4_process_level_ids = _listUnique([...(group.l4_process_level_ids || []), String(value)]);
        if (type === 'req') group.explore_requirement_ids = _listUnique([...(group.explore_requirement_ids || []), String(value)]);
        if (type === 'wricef') group.backlog_item_ids = _listUnique([...(group.backlog_item_ids || []), _toNum(value)].filter(Number.isFinite));
        if (type === 'config') group.config_item_ids = _listUnique([...(group.config_item_ids || []), _toNum(value)].filter(Number.isFinite));

        _activeTraceGroupIndex = index;
        _renderTraceabilityBasket();
    }

    function removeTraceChild(index, type, value) {
        const group = _traceabilityState.groups[index];
        if (!group) return;
        if (type === 'l4') group.l4_process_level_ids = (group.l4_process_level_ids || []).filter(v => String(v) !== String(value));
        if (type === 'req') group.explore_requirement_ids = (group.explore_requirement_ids || []).filter(v => String(v) !== String(value));
        if (type === 'wricef') group.backlog_item_ids = (group.backlog_item_ids || []).filter(v => String(v) !== String(value));
        if (type === 'config') group.config_item_ids = (group.config_item_ids || []).filter(v => String(v) !== String(value));
        _activeTraceGroupIndex = index;
        _renderTraceabilityBasket();
    }

    function toggleTraceExcluded(index, type, value, checked) {
        const group = _traceabilityState.groups[index];
        if (!group) return;
        if (type === 'req') {
            const base = (group.excluded_requirement_ids || []).map(String);
            group.excluded_requirement_ids = checked
                ? _listUnique([...base, String(value)])
                : base.filter(v => String(v) !== String(value));
        }
        if (type === 'wricef') {
            const base = (group.excluded_backlog_item_ids || []).map(_toNum).filter(Number.isFinite);
            const num = _toNum(value);
            group.excluded_backlog_item_ids = checked
                ? _listUnique([...base, num].filter(Number.isFinite))
                : base.filter(v => String(v) !== String(num));
        }
        if (type === 'config') {
            const base = (group.excluded_config_item_ids || []).map(_toNum).filter(Number.isFinite);
            const num = _toNum(value);
            group.excluded_config_item_ids = checked
                ? _listUnique([...base, num].filter(Number.isFinite))
                : base.filter(v => String(v) !== String(num));
        }
        _activeTraceGroupIndex = index;
        _renderTraceabilityBasket();
    }

    function addTraceManual(index, type) {
        const group = _traceabilityState.groups[index];
        if (!group) return;
        if (type === 'req') {
            const val = document.getElementById(`traceGroup_${index}_manual_req`)?.value;
            if (!val) return;
            group.manual_requirement_ids = _listUnique([...(group.manual_requirement_ids || []), String(val)]);
        }
        if (type === 'wricef') {
            const val = _toNum(document.getElementById(`traceGroup_${index}_manual_wricef`)?.value);
            if (!Number.isFinite(val)) return;
            group.manual_backlog_item_ids = _listUnique([...(group.manual_backlog_item_ids || []), val]);
        }
        if (type === 'config') {
            const val = _toNum(document.getElementById(`traceGroup_${index}_manual_config`)?.value);
            if (!Number.isFinite(val)) return;
            group.manual_config_item_ids = _listUnique([...(group.manual_config_item_ids || []), val]);
        }
        _activeTraceGroupIndex = index;
        _renderTraceabilityBasket();
    }

    function removeTraceManual(index, type, value) {
        const group = _traceabilityState.groups[index];
        if (!group) return;
        if (type === 'req') group.manual_requirement_ids = (group.manual_requirement_ids || []).filter(v => String(v) !== String(value));
        if (type === 'wricef') group.manual_backlog_item_ids = (group.manual_backlog_item_ids || []).filter(v => String(v) !== String(value));
        if (type === 'config') group.manual_config_item_ids = (group.manual_config_item_ids || []).filter(v => String(v) !== String(value));
        _activeTraceGroupIndex = index;
        _renderTraceabilityBasket();
    }

    async function saveTraceOverrides() {
        if (!_activeCaseId) return App.toast('Save the test case first to manage overrides', 'error');
        const traceGroups = _normalizeTraceGroups(_traceabilityState.groups || []);
        if (!traceGroups.length) return App.toast('At least one L3 scope is required', 'error');
        try {
            await API.put(`/testing/catalog/${_activeCaseId}/traceability-overrides`, {
                traceability_links: traceGroups,
            });
            await _refreshDerivedTraceabilityFromApi();
            App.toast('Traceability overrides saved', 'success');
        } catch (e) {
            App.toast(e.message || 'Failed to save overrides', 'error');
        }
    }

    function switchCaseWizard(step) {
        _caseWizardStep = step === 2 ? 2 : 1;
        const s1 = document.getElementById('caseWizardStep1');
        const s2 = document.getElementById('caseWizardStep2');
        if (s1) s1.style.display = _caseWizardStep === 1 ? '' : 'none';
        if (s2) s2.style.display = _caseWizardStep === 2 ? '' : 'none';
        document.querySelectorAll('.case-wizard-btn').forEach(btn => {
            btn.classList.toggle('active', Number(btn.dataset.cwstep) === _caseWizardStep);
        });
        if (_caseWizardStep === 2) {
            _renderL3CoveragePanel();
            refreshL3Coverage(false);
        }
    }

    function _isL3RequiredLayer(layer) {
        return ['unit', 'sit', 'uat'].includes(String(layer || '').toLowerCase());
    }

    function _updateTraceabilityRequirementUI() {
        const layer = document.getElementById('tcLayer')?.value || 'sit';
        const required = _isL3RequiredLayer(layer);
        const l3Label = document.getElementById('tcL3Label');
        const hint = document.getElementById('tcTraceRuleHint');
        if (l3Label) l3Label.textContent = required ? 'L3 Process *' : 'L3 Process';
        if (hint) {
            hint.style.color = required ? '#c4314b' : '#666';
            hint.textContent = required
                ? 'For UNIT/SIT/UAT, at least one L3 basket is required.'
                : 'For this layer, L3 is optional but recommended for traceability.';
        }
    }

    function _renderDraftSteps() {
        const container = document.getElementById('draftStepsContainer');
        if (!container) return;
        if (!_draftSteps.length) {
            container.innerHTML = '<p style="font-size:12px;color:#777">No steps yet.</p>';
            return;
        }
        container.innerHTML = `
            <table class="data-table" style="font-size:12px">
                <thead><tr><th style="width:60px">Step</th><th>Action *</th><th>Expected Result *</th><th style="width:70px"></th></tr></thead>
                <tbody>
                    ${_draftSteps.map((s, idx) => `
                        <tr>
                            <td>${idx + 1}</td>
                            <td><input class="form-control" value="${esc(s.action || '')}" oninput="TestPlanningView.updateDraftStep(${idx}, 'action', this.value)"></td>
                            <td><input class="form-control" value="${esc(s.expected_result || '')}" oninput="TestPlanningView.updateDraftStep(${idx}, 'expected_result', this.value)"></td>
                            <td><button type="button" class="btn btn-sm btn-danger" onclick="TestPlanningView.removeDraftStepRow(${idx})">🗑</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    function addDraftStepRow() {
        const next = (_draftSteps.length || 0) + 1;
        _draftSteps.push({ step_no: next, action: '', expected_result: '' });
        _renderDraftSteps();
    }

    function updateDraftStep(index, field, value) {
        if (!_draftSteps[index]) return;
        _draftSteps[index][field] = value;
    }

    function removeDraftStepRow(index) {
        _draftSteps.splice(index, 1);
        _renderDraftSteps();
    }

    // ── Structured Step Management ─────────────────────────────────────
    async function _loadSteps(caseId) {
        _currentCaseIdForSteps = caseId;
        const container = document.getElementById('stepsContainer');
        if (!container) return;
        try {
            _currentSteps = await API.get(`/testing/catalog/${caseId}/steps`);
            _renderStepsList();
        } catch (e) {
            container.innerHTML = `<p style="color:#c4314b">Could not load steps: ${esc(e.message)}</p>`;
        }
    }

    function _renderStepsList() {
        const container = document.getElementById('stepsContainer');
        if (!container) return;

        if (_currentSteps.length === 0) {
            container.innerHTML = `<p style="color:#999;font-size:13px">No steps defined. Click "+ Add Step" to add structured test steps.</p>`;
            return;
        }

        container.innerHTML = `
            <table class="data-table" style="font-size:13px">
                <thead><tr>
                    <th style="width:40px">#</th>
                    <th>Action</th>
                    <th>Expected Result</th>
                    <th style="width:100px">Test Data</th>
                    <th style="width:90px">Actions</th>
                </tr></thead>
                <tbody>
                    ${_currentSteps.map(s => `<tr id="stepRow_${s.id}">
                        <td style="text-align:center;font-weight:600">${s.step_no}</td>
                        <td>${esc(s.action)}</td>
                        <td>${esc(s.expected_result || '-')}</td>
                        <td>${esc(s.test_data || '-')}</td>
                        <td>
                            <button class="btn btn-sm" onclick="TestPlanningView.editStepRow(${s.id})" title="Edit">✏️</button>
                            <button class="btn btn-sm btn-danger" onclick="TestPlanningView.deleteStep(${s.id})" title="Delete">🗑</button>
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>
        `;
    }

    function addStepRow() {
        const container = document.getElementById('stepsContainer');
        if (!container) return;
        const noSteps = container.querySelector('p');
        if (noSteps) noSteps.remove();
        if (document.getElementById('newStepForm')) return;

        const maxNo = _currentSteps.reduce((max, s) => Math.max(max, s.step_no || 0), 0);
        const nextNo = maxNo + 1;

        const form = document.createElement('div');
        form.id = 'newStepForm';
        form.style.cssText = 'border:1px solid #d0d0d0;border-radius:6px;padding:12px;margin-top:8px;background:#fafafa';
        form.innerHTML = `
            <div style="display:flex;gap:8px;margin-bottom:8px">
                <div style="width:60px">
                    <label style="font-size:11px;color:#666">Step #</label>
                    <input id="newStepNo" class="form-control" type="number" value="${nextNo}" style="text-align:center">
                </div>
                <div style="flex:2">
                    <label style="font-size:11px;color:#666">Action *</label>
                    <input id="newStepAction" class="form-control" placeholder="e.g. Navigate to transaction VA01">
                </div>
            </div>
            <div style="display:flex;gap:8px;margin-bottom:8px">
                <div style="flex:1">
                    <label style="font-size:11px;color:#666">Expected Result</label>
                    <input id="newStepExpected" class="form-control" placeholder="e.g. Order creation screen opens">
                </div>
                <div style="flex:1">
                    <label style="font-size:11px;color:#666">Test Data</label>
                    <input id="newStepData" class="form-control" placeholder="e.g. Material: MAT-001">
                </div>
            </div>
            <div style="display:flex;gap:6px;justify-content:flex-end">
                <button class="btn btn-sm" onclick="document.getElementById('newStepForm').remove()">Cancel</button>
                <button class="btn btn-sm btn-primary" onclick="TestPlanningView.saveNewStep()">Save Step</button>
            </div>
        `;
        container.appendChild(form);
        document.getElementById('newStepAction').focus();
    }

    async function saveNewStep() {
        const action = document.getElementById('newStepAction').value.trim();
        if (!action) return App.toast('Action is required for the step', 'error');

        const body = {
            step_no: parseInt(document.getElementById('newStepNo').value) || 1,
            action: action,
            expected_result: document.getElementById('newStepExpected').value.trim(),
            test_data: document.getElementById('newStepData').value.trim(),
        };

        try {
            await API.post(`/testing/catalog/${_currentCaseIdForSteps}/steps`, body);
            App.toast('Step added', 'success');
            _currentSteps = await API.get(`/testing/catalog/${_currentCaseIdForSteps}/steps`);
            _renderStepsList();
        } catch (e) {
            App.toast('Failed to add step: ' + e.message, 'error');
        }
    }

    function editStepRow(stepId) {
        const step = _currentSteps.find(s => s.id === stepId);
        if (!step) return;
        const row = document.getElementById(`stepRow_${stepId}`);
        if (!row) return;

        row.innerHTML = `
            <td><input id="editStepNo_${stepId}" class="form-control" type="number" value="${step.step_no}" style="width:40px;text-align:center"></td>
            <td><input id="editStepAction_${stepId}" class="form-control" value="${esc(step.action)}"></td>
            <td><input id="editStepExpected_${stepId}" class="form-control" value="${esc(step.expected_result || '')}"></td>
            <td><input id="editStepData_${stepId}" class="form-control" value="${esc(step.test_data || '')}"></td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="TestPlanningView.updateStep(${stepId})">✓</button>
                <button class="btn btn-sm" onclick="TestPlanningView._loadSteps(${_currentCaseIdForSteps})">✕</button>
            </td>
        `;
    }

    async function updateStep(stepId) {
        const body = {
            step_no: parseInt(document.getElementById(`editStepNo_${stepId}`).value) || 1,
            action: document.getElementById(`editStepAction_${stepId}`).value.trim(),
            expected_result: document.getElementById(`editStepExpected_${stepId}`).value.trim(),
            test_data: document.getElementById(`editStepData_${stepId}`).value.trim(),
        };
        if (!body.action) return App.toast('Action is required', 'error');

        try {
            await API.put(`/testing/steps/${stepId}`, body);
            App.toast('Step updated', 'success');
            _currentSteps = await API.get(`/testing/catalog/${_currentCaseIdForSteps}/steps`);
            _renderStepsList();
        } catch (e) {
            App.toast('Failed to update step: ' + e.message, 'error');
        }
    }

    async function deleteStep(stepId) {
        if (!confirm('Delete this test step?')) return;
        try {
            await API.delete(`/testing/steps/${stepId}`);
            App.toast('Step deleted', 'success');
            _currentSteps = await API.get(`/testing/catalog/${_currentCaseIdForSteps}/steps`);
            _renderStepsList();
        } catch (e) {
            App.toast('Failed to delete step: ' + e.message, 'error');
        }
    }

    // ── Case Tab Switcher ─────────────────────────────────────────────
    function _switchCaseTab(tab) {
        document.querySelectorAll('.case-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.ctab === tab));
        document.querySelectorAll('.case-tab-panel').forEach(p => p.style.display = 'none');
        const panel = document.getElementById(`casePanel${tab.replace('case', '')}`);
        if (panel) panel.style.display = '';
    }

    // ── Performance Results ───────────────────────────────────────────
    async function _loadPerfResults(caseId) {
        try {
            const results = await API.get(`/testing/catalog/${caseId}/perf-results`);
            const el = document.getElementById('perfResultsContent');
            if (!el) return;
            if (results.length === 0) {
                el.innerHTML = '<p style="color:#999;text-align:center">No performance results recorded.</p>';
                return;
            }
            el.innerHTML = `
                <table class="data-table">
                    <thead><tr><th>Date</th><th>Response (ms)</th><th>Target (ms)</th><th>Pass/Fail</th><th>Throughput</th><th>Users</th><th>Env</th><th></th></tr></thead>
                    <tbody>
                        ${results.map(r => {
                            const pf = r.response_time_ms <= r.target_response_ms;
                            return `<tr>
                                <td style="font-size:12px;white-space:nowrap">${r.executed_at ? new Date(r.executed_at).toLocaleString() : '-'}</td>
                                <td><strong>${r.response_time_ms}</strong></td>
                                <td>${r.target_response_ms}</td>
                                <td><span class="badge" style="background:${pf ? '#107e3e' : '#c4314b'};color:#fff">${pf ? 'PASS' : 'FAIL'}</span></td>
                                <td>${r.throughput_rps || '-'}</td>
                                <td>${r.concurrent_users || '-'}</td>
                                <td>${esc(r.environment || '-')}</td>
                                <td><button class="btn btn-sm btn-danger" onclick="TestPlanningView.deletePerfResult(${r.id}, ${caseId})">🗑</button></td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>`;
            _renderPerfChart(results.slice().reverse());
        } catch(e) {
            const el = document.getElementById('perfResultsContent');
            if (el) el.innerHTML = `<p style="color:#c4314b">Error: ${esc(e.message)}</p>`;
        }
    }

    function _renderPerfChart(results) {
        const ctx = document.getElementById('chartPerfTrend');
        if (!ctx || !results.length) return;
        const labels = results.map((r, i) => r.executed_at ? new Date(r.executed_at).toLocaleDateString() : `#${i+1}`);
        const times = results.map(r => r.response_time_ms);
        const targets = results.map(r => r.target_response_ms);

        new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Response Time (ms)', data: times, borderColor: '#0070f3', backgroundColor: 'rgba(0,112,243,0.1)', fill: true, tension: 0.3, pointRadius: 4 },
                    { label: 'Target (ms)', data: targets, borderColor: '#c4314b', borderDash: [5, 5], fill: false, pointRadius: 0 },
                ],
            },
            options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: 'ms' } } }, plugins: { legend: { position: 'bottom' } } },
        });
    }

    async function addPerfResult(caseId) {
        const body = {
            response_time_ms: parseFloat(document.getElementById('perfResponseTime').value),
            target_response_ms: parseFloat(document.getElementById('perfTarget').value),
            throughput_rps: parseFloat(document.getElementById('perfThroughput').value) || null,
            concurrent_users: parseInt(document.getElementById('perfUsers').value) || null,
            environment: document.getElementById('perfEnv').value,
            notes: document.getElementById('perfNotes').value,
        };
        if (!body.response_time_ms || !body.target_response_ms) return App.toast('Response time and target are required', 'error');
        try {
            await API.post(`/testing/catalog/${caseId}/perf-results`, body);
            App.toast('Performance result added', 'success');
            document.getElementById('perfResponseTime').value = '';
            document.getElementById('perfTarget').value = '';
            await _loadPerfResults(caseId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    async function deletePerfResult(resultId, caseId) {
        if (!confirm('Delete this performance result?')) return;
        try {
            await API.delete(`/testing/perf-results/${resultId}`);
            App.toast('Deleted', 'success');
            await _loadPerfResults(caseId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    // ── Case Dependencies ─────────────────────────────────────────────
    async function _loadCaseDependencies(caseId) {
        try {
            const data = await API.get(`/testing/catalog/${caseId}/dependencies`);
            const el = document.getElementById('caseDepsContent');
            if (!el) return;
            const blockedBy = data.blocked_by || [];
            const blocks = data.blocks || [];
            if (blockedBy.length === 0 && blocks.length === 0) {
                el.innerHTML = '<p style="color:#999;text-align:center">No dependencies defined.</p>';
                return;
            }
            const typeBadge = (t) => {
                const c = { blocks: '#c4314b', related: '#0070f3', data_feeds: '#6a4fa0' };
                return `<span class="badge" style="background:${c[t]||'#888'};color:#fff">${t}</span>`;
            };
            const resultBadge = (r) => {
                const c = { pass: '#107e3e', fail: '#c4314b', blocked: '#e9730c', not_run: '#888' };
                return `<span class="badge" style="background:${c[r]||'#888'};color:#fff">${r}</span>`;
            };
            let html = '';
            if (blockedBy.length > 0) {
                html += `<h4 style="color:#c4314b;margin-bottom:4px">🔴 Blocked By (${blockedBy.length})</h4>
                <table class="data-table"><thead><tr><th>Case</th><th>Type</th><th>Last Result</th><th>Notes</th><th></th></tr></thead><tbody>
                    ${blockedBy.map(d => `<tr>
                        <td><strong>${esc(d.other_case_code || '#'+d.predecessor_id)}</strong> ${esc(d.other_case_title || '')}</td>
                        <td>${typeBadge(d.dependency_type)}</td>
                        <td>${resultBadge(d.other_last_result)}</td>
                        <td>${esc(d.notes || '-')}</td>
                        <td><button class="btn btn-sm btn-danger" onclick="TestPlanningView.deleteCaseDependency(${d.id}, ${caseId})">🗑</button></td>
                    </tr>`).join('')}</tbody></table>`;
            }
            if (blocks.length > 0) {
                html += `<h4 style="color:#e9730c;margin:12px 0 4px">🟠 Blocks (${blocks.length})</h4>
                <table class="data-table"><thead><tr><th>Case</th><th>Type</th><th>Last Result</th><th>Notes</th><th></th></tr></thead><tbody>
                    ${blocks.map(d => `<tr>
                        <td><strong>${esc(d.other_case_code || '#'+d.successor_id)}</strong> ${esc(d.other_case_title || '')}</td>
                        <td>${typeBadge(d.dependency_type)}</td>
                        <td>${resultBadge(d.other_last_result)}</td>
                        <td>${esc(d.notes || '-')}</td>
                        <td><button class="btn btn-sm btn-danger" onclick="TestPlanningView.deleteCaseDependency(${d.id}, ${caseId})">🗑</button></td>
                    </tr>`).join('')}</tbody></table>`;
            }
            el.innerHTML = html;
        } catch(e) {
            const el = document.getElementById('caseDepsContent');
            if (el) el.innerHTML = `<p style="color:#c4314b">Error: ${esc(e.message)}</p>`;
        }
    }

    async function addCaseDependency(caseId) {
        const otherId = parseInt(document.getElementById('depOtherCaseId').value);
        if (!otherId) return App.toast('Test case ID is required', 'error');
        const body = {
            other_case_id: otherId,
            direction: document.getElementById('depDirection').value,
            dependency_type: document.getElementById('depType').value,
        };
        try {
            await API.post(`/testing/catalog/${caseId}/dependencies`, body);
            App.toast('Dependency added', 'success');
            document.getElementById('depOtherCaseId').value = '';
            await _loadCaseDependencies(caseId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    async function deleteCaseDependency(depId, caseId) {
        if (!confirm('Remove this dependency?')) return;
        try {
            await API.delete(`/testing/dependencies/${depId}`);
            App.toast('Dependency removed', 'success');
            await _loadCaseDependencies(caseId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    async function saveCase(id) {
        const pid = TestingShared.pid;
        const _selectedSuiteIds = () => {
            const el = document.getElementById('tcSuiteId');
            if (!el) return [];
            return Array.from(el.selectedOptions || [])
                .map(o => parseInt(o.value, 10))
                .filter(Number.isInteger);
        };
        const suiteIds = _selectedSuiteIds();
        const selectedLayer = document.getElementById('tcLayer').value;
        const traceGroups = _normalizeTraceGroups(_traceabilityState.groups || []);
        const firstGroup = traceGroups[0] || null;
        const selectedProcessLevelId = firstGroup ? firstGroup.l3_process_level_id : null;
        const selectedExploreReqId = firstGroup ? ((firstGroup.explore_requirement_ids || [])[0] || null) : null;
        const selectedBacklogItemId = firstGroup ? ((firstGroup.backlog_item_ids || [])[0] || null) : null;
        const selectedConfigItemId = firstGroup ? ((firstGroup.config_item_ids || [])[0] || null) : null;
        const body = {
            code: document.getElementById('tcCode')?.value?.trim(),
            title: document.getElementById('tcTitle').value,
            test_layer: selectedLayer,
            test_type: document.getElementById('tcType')?.value || 'functional',
            module: document.getElementById('tcModule').value,
            priority: document.getElementById('tcPriority').value,
            risk: document.getElementById('tcRisk')?.value || 'medium',
            status: document.getElementById('tcStatus')?.value || 'draft',
            description: document.getElementById('tcDesc').value,
            preconditions: document.getElementById('tcPrecond').value,
            test_steps: document.getElementById('tcSteps') ? document.getElementById('tcSteps').value : '',
            expected_result: document.getElementById('tcExpected').value,
            test_data_set: document.getElementById('tcData').value,
            data_readiness: document.getElementById('tcDataReadiness')?.value || '',
            assigned_to: document.getElementById('tcAssigned').value,
            reviewer: document.getElementById('tcReviewer')?.value || '',
            version: document.getElementById('tcVersion')?.value || '1.0',
            assigned_to_id: document.getElementById('tcAssigned').value || null,
            is_regression: document.getElementById('tcRegression').checked,
            suite_ids: suiteIds,
            process_level_id: selectedProcessLevelId,
            explore_requirement_id: selectedExploreReqId,
            backlog_item_id: selectedBacklogItemId,
            config_item_id: selectedConfigItemId,
            traceability_links: traceGroups,
        };
        if (!body.code) return App.toast('Test Case Code is required', 'error');
        if (!body.title) return App.toast('Title is required', 'error');
        if (!body.priority) return App.toast('Priority is required', 'error');
        if (!body.preconditions || !body.preconditions.trim()) return App.toast('Preconditions are required', 'error');
        if (_isL3RequiredLayer(selectedLayer)) {
            if (!traceGroups.length) {
                return App.toast('At least one L3 basket is required for UNIT/SIT/UAT.', 'error');
            }
        }
        if (selectedLayer === 'sit') {
            if (!body.module || !body.module.trim()) return App.toast('Module is required for SIT', 'error');
            if (!body.risk) return App.toast('Risk is required for SIT', 'error');
            const hasDataReadiness = (body.test_data_set && body.test_data_set.trim()) || (body.data_readiness && body.data_readiness.trim());
            if (!hasDataReadiness) {
                return App.toast('For SIT, provide linked data set or data readiness notes', 'error');
            }
        }

        if (!id) {
            const validDraftSteps = (_draftSteps || []).filter(s => (s.action || '').trim() || (s.expected_result || '').trim());
            if (!validDraftSteps.length) return App.toast('At least one test step is required', 'error');
            if (validDraftSteps.some(s => !(s.action || '').trim() || !(s.expected_result || '').trim())) {
                return App.toast('Each step must include Action and Expected Result', 'error');
            }
            body.test_steps = validDraftSteps.map((s, i) => `${i + 1}. ${s.action}`).join('\n');
            body.expected_result = validDraftSteps.map((s, i) => `${i + 1}. ${s.expected_result}`).join('\n');
        }

        if (id) {
            await API.put(`/testing/catalog/${id}`, body);
            App.toast('Test case updated', 'success');
        } else {
            const created = await API.post(`/programs/${pid}/testing/catalog`, body);
            const createdId = created?.id;
            const validDraftSteps = (_draftSteps || []).filter(s => (s.action || '').trim() && (s.expected_result || '').trim());
            for (let i = 0; createdId && i < validDraftSteps.length; i += 1) {
                const s = validDraftSteps[i];
                await API.post(`/testing/catalog/${createdId}/steps`, {
                    step_no: i + 1,
                    action: s.action.trim(),
                    expected_result: s.expected_result.trim(),
                });
            }
            App.toast('Test case created', 'success');
        }
        App.closeModal();
        await renderCatalog();
    }

    async function showCaseDetail(id) {
        App.navigate('test-case-detail', id);
    }

    async function deleteCase(id) {
        if (!confirm('Delete this test case?')) return;
        await API.delete(`/testing/catalog/${id}`);
        App.toast('Test case deleted', 'success');
        await renderCatalog();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // SUITES TAB
    // ═══════════════════════════════════════════════════════════════════════
    const SUITE_STATUSES = ['draft', 'active', 'locked', 'archived'];

    async function renderSuites() {
        const pid = TestingShared.pid;
        const res = await API.get(`/programs/${pid}/testing/suites`);
        testSuites = res.items || res || [];
        const container = document.getElementById('testContent');

        if (testSuites.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📦</div>
                    <div class="empty-state__title">No test suites yet</div>
                    <p>Create a suite to group related test cases.</p><br>
                    <button class="btn btn-primary" onclick="TestPlanningView.showSuiteModal()">+ New Suite</button>
                </div>`;
            return;
        }
        container.innerHTML = `
            <div class="tm-toolbar">
                <div class="tm-toolbar__left">
                    <input id="tmSuiteSearch" class="tm-input" placeholder="Search suites..." value="${esc(_suiteSearch)}" />
                    <span id="suiteItemCount" class="tm-muted"></span>
                </div>
                <div class="tm-toolbar__right">
                    <button class="btn btn-primary btn-sm" onclick="TestPlanningView.showSuiteModal()">+ New Suite</button>
                </div>
            </div>
            <div id="suiteSplitRoot"></div>
        `;

        const searchEl = document.getElementById('tmSuiteSearch');
        if (searchEl) {
            searchEl.addEventListener('input', (e) => {
                _suiteSearch = e.target.value || '';
                applySuiteFilter();
            });
        }

        applySuiteFilter();
    }

    function renderSuiteFilterBar() {
        const el = document.getElementById('suiteFilterBar');
        if (!el) return;
        el.innerHTML = ExpUI.filterBar({
            id: 'suiteFB',
            searchPlaceholder: 'Search suites…',
            searchValue: _suiteSearch,
            onSearch: 'TestPlanningView.setSuiteSearch(this.value)',
            onChange: 'TestPlanningView.onSuiteFilterChange',
            filters: [
                {
                    id: 'suite_purpose', label: 'Purpose', type: 'multi', color: '#3b82f6',
                    options: [...new Set(testSuites.map(s => (s.purpose || s.suite_type || 'General').trim()).filter(Boolean))]
                        .sort()
                        .map(p => ({ value: p, label: p })),
                    selected: _suiteFilters.suite_purpose || [],
                },
                {
                    id: 'status', label: 'Status', type: 'multi', color: '#10b981',
                    options: SUITE_STATUSES.map(s => ({ value: s, label: s.charAt(0).toUpperCase() + s.slice(1) })),
                    selected: _suiteFilters.status || [],
                },
                {
                    id: 'module', label: 'Module', type: 'multi', color: '#8b5cf6',
                    options: [...new Set(testSuites.map(s => s.module).filter(Boolean))].sort().map(m => ({ value: m, label: m })),
                    selected: _suiteFilters.module || [],
                },
            ],
            actionsHtml: `<span style="font-size:12px;color:#94a3b8" id="suiteItemCount"></span>
                <button class="btn btn-primary btn-sm" onclick="TestPlanningView.showSuiteModal()">+ New Suite</button>`,
        });
    }

    function setSuiteSearch(val) {
        _suiteSearch = val;
        applySuiteFilter();
    }

    function onSuiteFilterChange(update) {
        if (update._clearAll) {
            _suiteFilters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete _suiteFilters[key];
                } else {
                    _suiteFilters[key] = val;
                }
            });
        }
        renderSuiteFilterBar();
        applySuiteFilter();
    }

    function applySuiteFilter() {
        let filtered = [...testSuites];

        if (_suiteSearch) {
            const q = _suiteSearch.toLowerCase();
            filtered = filtered.filter(s =>
                (s.name || '').toLowerCase().includes(q) ||
                (s.module || '').toLowerCase().includes(q) ||
                (s.owner || '').toLowerCase().includes(q) ||
                (s.tags || '').toLowerCase().includes(q)
            );
        }

        Object.entries(_suiteFilters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (values.length === 0) return;
            if (key === 'suite_purpose') {
                filtered = filtered.filter(s => values.includes(String((s.purpose || s.suite_type || 'General').trim())));
            } else {
                filtered = filtered.filter(s => values.includes(String(s[key])));
            }
        });

        if (_suiteTreeFilter && _suiteTreeFilter !== 'all') {
            const [kind, value] = String(_suiteTreeFilter).split(':');
            if (kind === 'purpose') {
                filtered = filtered.filter(s => String((s.purpose || s.suite_type || 'General').trim()) === value);
            }
            if (kind === 'status') {
                filtered = filtered.filter(s => String(s.status || '') === value);
            }
            if (kind === 'module') {
                filtered = filtered.filter(s => String(s.module || '') === value);
            }
        }

        const countEl = document.getElementById('suiteItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${testSuites.length}`;

        _renderSuiteSplit(filtered);
    }

    function _buildSuiteTreeNodes() {
        const nodes = [{ id: 'all', label: 'All Suites', count: testSuites.length }];
        const purposes = new Map();
        const statuses = new Map();
        const modules = new Map();

        testSuites.forEach(s => {
            const purpose = (s.purpose || s.suite_type || 'General').trim();
            const status = s.status || 'draft';
            const module = s.module || 'Unassigned';
            purposes.set(purpose, (purposes.get(purpose) || 0) + 1);
            statuses.set(status, (statuses.get(status) || 0) + 1);
            modules.set(module, (modules.get(module) || 0) + 1);
        });

        [...purposes.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([value, count]) => {
            nodes.push({ id: `purpose:${value}`, label: `Purpose: ${value}`, count });
        });
        [...statuses.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([value, count]) => {
            nodes.push({ id: `status:${value}`, label: `Status: ${value}`, count });
        });
        [...modules.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([value, count]) => {
            nodes.push({ id: `module:${value}`, label: `Module: ${value}`, count });
        });

        return nodes;
    }

    function _renderSuiteSplit(list) {
        const root = document.getElementById('suiteSplitRoot');
        if (!root) return;

        if (!window.TMSplitPane || !window.TMTreePanel || !window.TMDataGrid) {
            root.innerHTML = _renderSuiteTable(list);
            return;
        }

        TMSplitPane.mount(root, {
            leftHtml: '<div id="tmSuiteTree"></div>',
            rightHtml: '<div id="tmSuiteGrid" style="padding:8px"></div>',
            leftWidth: 260,
            minLeft: 180,
            maxLeft: 440,
        });

        const treeEl = document.getElementById('tmSuiteTree');
        const gridEl = document.getElementById('tmSuiteGrid');
        if (!treeEl || !gridEl) return;

        TMTreePanel.render(treeEl, {
            title: 'Suite Groups',
            nodes: _buildSuiteTreeNodes(),
            selectedId: _suiteTreeFilter,
            searchPlaceholder: 'Search group...',
            onSelect: (nodeId) => {
                _suiteTreeFilter = nodeId;
                applySuiteFilter();
            },
        });

        const purposeBadge = (suite) => {
            const txt = (suite.purpose || suite.suite_type || 'General').trim();
            return `<span class="badge" style="background:#6a4fa0;color:#fff">${esc(txt)}</span>`;
        };
        const statusBadge = (status) => {
            const colors = { draft: '#888', active: '#0070f3', locked: '#e9730c', archived: '#555' };
            return `<span class="badge" style="background:${colors[status] || '#888'};color:#fff">${status || '-'}</span>`;
        };

        TMDataGrid.render(gridEl, {
            rows: list,
            rowKey: 'id',
            emptyText: 'No suites match your filters.',
            onRowClick: (rowId) => TestPlanningView.showSuiteDetail(Number(rowId)),
            columns: [
                { key: 'name', label: 'Name', width: '220px', render: (s) => `<strong>${esc(s.name || '-')}</strong>` },
                { key: 'purpose', label: 'Purpose', width: '160px', render: (s) => purposeBadge(s) },
                { key: 'status', label: 'Status', width: '100px', render: (s) => statusBadge(s.status) },
                { key: 'module', label: 'Module', width: '95px', render: (s) => esc(s.module || '-') },
                { key: 'owner', label: 'Owner', width: '120px', render: (s) => esc(s.owner || '-') },
                { key: 'tags', label: 'Tags', width: 'auto', render: (s) => esc(s.tags || '-') },
                {
                    key: 'actions', label: '', width: '78px', align: 'center', render: (s) =>
                        `<button class="btn btn-sm" onclick="event.stopPropagation();TestPlanningView.editSuite(${s.id})">✏️</button>
                         <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();TestPlanningView.deleteSuite(${s.id})">🗑</button>`,
                },
            ],
        });
    }

    function _renderSuiteTable(list) {
        const purposeBadge = (suite) => {
            const txt = (suite.purpose || suite.suite_type || 'General').trim();
            return `<span class="badge" style="background:#6a4fa0;color:#fff">${esc(txt)}</span>`;
        };
        const statusBadge = (s) => {
            const colors = { draft: '#888', active: '#0070f3', locked: '#e9730c', archived: '#555' };
            return `<span class="badge" style="background:${colors[s] || '#888'};color:#fff">${s}</span>`;
        };
        return `<table class="data-table">
                <thead><tr>
                    <th>Name</th><th>Purpose</th><th>Status</th><th>Module</th><th>Owner</th><th>Tags</th><th>Actions</th>
                </tr></thead>
                <tbody>
                    ${list.map(s => `<tr onclick="TestPlanningView.showSuiteDetail(${s.id})" style="cursor:pointer" class="clickable-row">
                        <td><strong>${esc(s.name)}</strong></td>
                        <td>${purposeBadge(s)}</td>
                        <td>${statusBadge(s.status)}</td>
                        <td>${esc(s.module || '-')}</td>
                        <td>${esc(s.owner || '-')}</td>
                        <td>${esc(s.tags || '-')}</td>
                        <td>
                            <button class="btn btn-sm" onclick="event.stopPropagation();TestPlanningView.editSuite(${s.id})">✏️</button>
                            <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();TestPlanningView.deleteSuite(${s.id})">🗑</button>
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>`;
    }

    async function filterSuites() {
        // Legacy — kept for compatibility; now uses client-side filter
        applySuiteFilter();
    }

    function showSuiteModal(suite = null) {
        const isEdit = !!suite;
        const title = isEdit ? 'Edit Test Suite' : 'New Test Suite';
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label>
                    <input id="suiteName" class="form-control" value="${isEdit ? esc(suite.name) : ''}"></div>
                <div class="form-row">
                    <div class="form-group"><label>Legacy Suite Type (Read-only)</label>
                        <input id="suiteTypeLegacy" class="form-control" value="${esc((isEdit ? (suite.suite_type || 'Custom') : 'Custom'))}" readonly>
                    </div>
                    <div class="form-group"><label>Purpose</label>
                        <input id="suitePurpose" class="form-control" value="${isEdit ? esc(suite.purpose || '') : ''}" placeholder="e.g. E2E order flow, FI regression pack"></div>
                    <div class="form-group"><label>Status</label>
                        <select id="suiteStatus" class="form-control">
                            ${SUITE_STATUSES.map(s =>
                                `<option value="${s}" ${(isEdit && suite.status === s) ? 'selected' : ''}>${s}</option>`).join('')}
                        </select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Module</label>
                        <input id="suiteModule" class="form-control" value="${isEdit ? esc(suite.module || '') : ''}" placeholder="FI, MM, SD..."></div>
                    <div class="form-group"><label>Owner</label>
                        <input id="suiteOwner" class="form-control" value="${isEdit ? esc(suite.owner || '') : ''}"></div>
                </div>
                <div class="form-group"><label>Description</label>
                    <textarea id="suiteDesc" class="form-control" rows="2">${isEdit ? esc(suite.description || '') : ''}</textarea></div>
                <div class="form-group"><label>Tags</label>
                    <input id="suiteTags" class="form-control" value="${isEdit ? esc(suite.tags || '') : ''}" placeholder="e.g. smoke, critical-path"></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanningView.saveSuite(${isEdit ? suite.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `;
        document.getElementById('modalOverlay').classList.add('open');
    }

    async function saveSuite(id) {
        const pid = TestingShared.pid;
        const body = {
            name: document.getElementById('suiteName').value,
            suite_type: document.getElementById('suiteTypeLegacy').value,
            purpose: document.getElementById('suitePurpose').value,
            status: document.getElementById('suiteStatus').value,
            module: document.getElementById('suiteModule').value,
            owner: document.getElementById('suiteOwner').value,
            description: document.getElementById('suiteDesc').value,
            tags: document.getElementById('suiteTags').value,
        };
        if (!body.name) return App.toast('Name is required', 'error');

        if (id) {
            await API.put(`/testing/suites/${id}`, body);
            App.toast('Suite updated', 'success');
        } else {
            await API.post(`/programs/${pid}/testing/suites`, body);
            App.toast('Suite created', 'success');
        }
        App.closeModal();
        await renderSuites();
    }

    async function editSuite(id) {
        const suite = await API.get(`/testing/suites/${id}`);
        showSuiteModal(suite);
    }

    async function showSuiteDetail(id) {
        const pid = TestingShared.pid;
        const suite = await API.get(`/testing/suites/${id}?include_cases=true`);
        const cases = suite.test_cases || [];
        const modal = document.getElementById('modalContainer');

        const purposeBadge = (suiteObj) => {
            const txt = (suiteObj.purpose || suiteObj.suite_type || 'General').trim();
            return `<span class="badge" style="background:#6a4fa0;color:#fff">${esc(txt)}</span>`;
        };
        const statusBadge = (s) => {
            const colors = { draft: '#888', active: '#0070f3', locked: '#e9730c', archived: '#555' };
            return `<span class="badge" style="background:${colors[s] || '#888'};color:#fff">${s}</span>`;
        };

        modal.innerHTML = `
            <div class="modal-header"><h2>📦 ${esc(suite.name)}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap">
                    <span>${purposeBadge(suite)}</span>
                    <span>${statusBadge(suite.status)}</span>
                    ${suite.module ? `<span><strong>Module:</strong> ${esc(suite.module)}</span>` : ''}
                    ${suite.owner ? `<span><strong>Owner:</strong> ${esc(suite.owner)}</span>` : ''}
                </div>
                ${suite.description ? `<p style="color:var(--sap-text-secondary);margin-bottom:12px">${esc(suite.description)}</p>` : ''}
                ${suite.tags ? `<p style="font-size:12px;color:var(--sap-text-secondary)">Tags: ${esc(suite.tags)}</p>` : ''}
                <hr style="margin:12px 0">
                <h3 style="margin-bottom:8px">Test Cases (${cases.length})</h3>
                ${cases.length === 0
                    ? '<p style="color:var(--sap-text-secondary)">No test cases assigned to this suite. Assign cases from the Catalog tab.</p>'
                    : `<table class="data-table">
                        <thead><tr><th>Code</th><th>Title</th><th>Layer</th><th>Status</th><th>Priority</th></tr></thead>
                        <tbody>
                            ${cases.map(tc => `<tr>
                                <td><span style="font-family:'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;font-weight:500;color:#1e3a5f;letter-spacing:-0.2px">${esc(tc.code || '-')}</span></td>
                                <td>${esc(tc.title)}</td>
                                <td>${(tc.test_layer || '-').toUpperCase()}</td>
                                <td>${esc(tc.status)}</td>
                                <td>${esc(tc.priority)}</td>
                            </tr>`).join('')}
                        </tbody>
                    </table>`}
            </div>
            <div class="modal-footer">
                <button class="btn btn-sm btn-secondary" onclick="TestPlanningView.showGenerateWricefModal(${suite.id})">Generate from WRICEF</button>
                <button class="btn btn-sm btn-secondary" onclick="TestPlanningView.showGenerateProcessModal(${suite.id})">Generate from Process</button>
                <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
                <button class="btn btn-primary" onclick="TestPlanningView.editSuite(${suite.id});App.closeModal()">Edit</button>
            </div>
        `;
        document.getElementById('modalOverlay').classList.add('open');
    }

    // ── Generate from WRICEF Modal ────────────────────────────────────
    async function showGenerateWricefModal(suiteId) {
        const pid = TestingShared.pid;
        App.closeModal();
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>⚙ Generate Test Cases from WRICEF</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body" style="max-height:65vh;overflow-y:auto">
                <p style="color:#666;margin-bottom:12px">Select WRICEF/Backlog items to auto-generate test cases from.</p>
                <div id="wricefItemList"><div class="spinner" style="margin:16px auto"></div></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanningView.executeGenerateWricef(${suiteId})">Generate</button>
            </div>
        `;
        overlay.classList.add('open');

        try {
            const items = await API.get(`/programs/${pid}/backlog`);
            const list = Array.isArray(items) ? items : (items.items || []);
            const el = document.getElementById('wricefItemList');
            if (list.length === 0) {
                el.innerHTML = '<p style="color:#999">No WRICEF/backlog items found.</p>';
                return;
            }
            el.innerHTML = `
                <div style="margin-bottom:8px"><label><input type="checkbox" id="wricefSelectAll" onchange="document.querySelectorAll('.wricef-cb').forEach(c=>c.checked=this.checked)"> <strong>Select All</strong></label></div>
                <div style="max-height:350px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:6px;padding:8px">
                    ${list.map(item => `
                        <label style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #f0f0f0;cursor:pointer">
                            <input type="checkbox" class="wricef-cb" value="${item.id}">
                            <span><span style="font-family:'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;font-weight:500;color:#1e3a5f">${esc(item.code || '')}</span> ${esc(item.title)} <span class="badge" style="font-size:10px">${esc(item.type || '')}</span></span>
                        </label>
                    `).join('')}
                </div>`;
        } catch(e) {
            document.getElementById('wricefItemList').innerHTML = `<p style="color:#c4314b">Error: ${esc(e.message)}</p>`;
        }
    }

    async function executeGenerateWricef(suiteId) {
        const ids = Array.from(document.querySelectorAll('.wricef-cb:checked')).map(cb => parseInt(cb.value));
        if (ids.length === 0) return App.toast('Select at least one item', 'error');
        try {
            const result = await API.post(`/testing/suites/${suiteId}/generate-from-wricef`, { wricef_item_ids: ids });
            App.toast(`Generated ${result.count} test case(s)`, 'success');
            App.closeModal();
        } catch(e) {
            App.toast('Generation failed: ' + e.message, 'error');
        }
    }

    // ── Generate from Process Modal ───────────────────────────────────
    async function showGenerateProcessModal(suiteId) {
        const pid = TestingShared.pid;
        App.closeModal();
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>🔄 Generate Test Cases from Process</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body" style="max-height:65vh;overflow-y:auto">
                <p style="color:#666;margin-bottom:12px">Select Explore L3 process levels to generate E2E test scenarios.</p>
                <div class="form-row">
                    <div class="form-group"><label>Test Level</label>
                        <select id="genTestLevel" class="form-control">
                            <option value="sit">SIT</option>
                            <option value="uat">UAT</option>
                            <option value="regression">Regression</option>
                        </select></div>
                    <div class="form-group"><label>UAT Category</label>
                        <input id="genUatCategory" class="form-control" placeholder="e.g. happy_path"></div>
                </div>
                <div id="processItemList"><div class="spinner" style="margin:16px auto"></div></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanningView.executeGenerateProcess(${suiteId})">Generate</button>
            </div>
        `;
        overlay.classList.add('open');

        try {
            const levels = await API.get(`/explore/process-levels?project_id=${pid}`);
            const l3Items = (Array.isArray(levels) ? levels : []).filter(l => l.level === 3);
            const el = document.getElementById('processItemList');
            if (l3Items.length === 0) {
                el.innerHTML = '<p style="color:#999">No L3 process levels found. Seed Explore data first.</p>';
                return;
            }
            el.innerHTML = `
                <div style="margin-bottom:8px"><label><input type="checkbox" id="processSelectAll" onchange="document.querySelectorAll('.process-cb').forEach(c=>c.checked=this.checked)"> <strong>Select All</strong></label></div>
                <div style="max-height:300px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:6px;padding:8px">
                    ${l3Items.map(l => `
                        <label style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #f0f0f0;cursor:pointer">
                            <input type="checkbox" class="process-cb" value="${l.id}">
                            <span><strong>${esc(l.code || '')}</strong> ${esc(l.name)} <span class="badge" style="font-size:10px">L${l.level}</span></span>
                        </label>
                    `).join('')}
                </div>`;
        } catch(e) {
            document.getElementById('processItemList').innerHTML = `<p style="color:#c4314b">Error: ${esc(e.message)}</p>`;
        }
    }

    async function executeGenerateProcess(suiteId) {
        const pid = TestingShared.pid;
        const ids = Array.from(document.querySelectorAll('.process-cb:checked')).map(cb => parseInt(cb.value));
        if (ids.length === 0) return App.toast('Select at least one process level', 'error');
        const testLevel = document.getElementById('genTestLevel')?.value || 'sit';
        const uatCategory = document.getElementById('genUatCategory')?.value || '';
        try {
            const result = await API.post(`/testing/suites/${suiteId}/generate-from-process`, {
                scope_item_ids: ids, test_level: testLevel, uat_category: uatCategory
            });
            App.toast(`Generated ${result.count} test case(s) from process`, 'success');
            App.closeModal();
        } catch(e) {
            App.toast('Generation failed: ' + e.message, 'error');
        }
    }

    async function deleteSuite(id) {
        if (!confirm('Delete this test suite? Test cases will be unlinked but not deleted.')) return;
        await API.delete(`/testing/suites/${id}`);
        App.toast('Suite deleted', 'success');
        await renderSuites();
    }

    // ── Public API ─────────────────────────────────────────────────────
    return {
        render,
        switchTab,
        // Plans
        showPlanModal, savePlan, deletePlan,
        // Catalog
        showCaseModal, saveCase, showCaseDetail, deleteCase, filterCatalog,
        setCatalogSearch, onCatalogFilterChange,
        // Suites
        showSuiteModal, saveSuite, editSuite, showSuiteDetail, deleteSuite, filterSuites,
        setSuiteSearch, onSuiteFilterChange,
        // Steps
        addStepRow, saveNewStep, editStepRow, updateStep, deleteStep, _loadSteps,
        addDraftStepRow, updateDraftStep, removeDraftStepRow,
        // Case tabs
        _switchCaseTab, addPerfResult, deletePerfResult,
        addCaseDependency, deleteCaseDependency,
        // Traceability B
        addTraceChild, removeTraceChild, removeTraceGroup, changeTraceGroupL3, clearTraceGroups,
        openTraceGroupDetail, closeTraceGroupDetail, switchCaseWizard,
        toggleTraceExcluded, addTraceManual, removeTraceManual, saveTraceOverrides,
        refreshL3Coverage, onL3CoverageSelect,
        // Generate
        showGenerateWricefModal, executeGenerateWricef,
        showGenerateProcessModal, executeGenerateProcess,
    };
})();
