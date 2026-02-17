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
    let _suiteSearch = '';
    let _suiteFilters = {};

    // ── Structured Step state ──────────────────────────────────────────
    let _currentSteps = [];
    let _currentCaseIdForSteps = null;

    // ── Main render ───────────────────────────────────────────────────
    async function render() {
        const pid = TestingShared.getProgram();
        const main = document.getElementById('mainContent');

        if (!pid) {
            main.innerHTML = TestingShared.noProgramHtml('Test Planning');
            return;
        }

        main.innerHTML = `
            <div class="page-header"><h1>📋 Test Planning</h1></div>
            <div class="tabs" id="testPlanningTabs">
                <div class="tab active" data-tab="catalog" onclick="TestPlanningView.switchTab('catalog')">📋 Test Cases</div>
                <div class="tab" data-tab="suites" onclick="TestPlanningView.switchTab('suites')">📦 Test Suites</div>
                <div class="tab" data-tab="plans" onclick="TestPlanningView.switchTab('plans')">📅 Test Plans</div>
            </div>
            <div class="card" id="testContent">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>
        `;
        await loadTabData();
    }

    function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('#testPlanningTabs .tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
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

        const STATUS_CLR = { draft: '#888', active: '#0070f3', completed: '#107e3e', cancelled: '#c4314b' };
        const TYPE_LBL = { sit: 'SIT', uat: 'UAT', regression: 'Regression', e2e: 'E2E', cutover_rehearsal: 'Cutover', performance: 'Performance' };

        if (plans.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📅</div>
                    <div class="empty-state__title">Henüz test planı yok</div>
                    <p>İlk test planınızı oluşturun, sonra scope (L3 süreç, senaryo, gereksinim) ekleyin.</p><br>
                    <button class="btn btn-primary" onclick="TestPlanningView.showPlanModal()">+ Yeni Test Planı</button>
                </div>`;
            return;
        }

        let html = `
            <div style="display:flex;justify-content:space-between;margin-bottom:16px">
                <h3 style="margin:0">Test Planları (${plans.length})</h3>
                <button class="btn btn-primary" onclick="TestPlanningView.showPlanModal()">+ Yeni Test Planı</button>
            </div>
            <table class="data-table">
                <thead><tr>
                    <th>Plan Adı</th><th>Tip</th><th>Ortam</th><th>Durum</th><th>Başlangıç</th><th>Bitiş</th><th>İşlemler</th>
                </tr></thead>
                <tbody>
                    ${plans.map(p => `<tr>
                        <td><strong>${esc(p.name)}</strong>${p.description ? `<div style="color:#666;font-size:12px">${esc(p.description)}</div>` : ''}</td>
                        <td><span class="badge" style="background:#0070f3;color:#fff">${TYPE_LBL[p.plan_type] || p.plan_type || '—'}</span></td>
                        <td>${p.environment ? `<span class="badge" style="background:#6a4fa0;color:#fff">${esc(p.environment)}</span>` : '—'}</td>
                        <td><span class="badge" style="background:${STATUS_CLR[p.status] || '#888'};color:#fff">${esc(p.status)}</span></td>
                        <td>${p.start_date || '—'}</td>
                        <td>${p.end_date || '—'}</td>
                        <td style="display:flex;gap:4px">
                            <button class="btn btn-sm" style="background:#C08B5C;color:#fff" onclick="TestPlanDetailView.open(${p.id})" title="Plan detayı: Scope, TC, Data, Cycles">📊 Detay</button>
                            <button class="btn btn-sm btn-danger" onclick="TestPlanningView.deletePlan(${p.id})">🗑</button>
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>`;
        container.innerHTML = html;
    }

    function showPlanModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>Yeni Test Planı</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Plan Adı *</label>
                    <input id="planName" class="form-control" placeholder="ör. SIT Master Plan"></div>
                <div class="form-group"><label>Açıklama</label>
                    <textarea id="planDesc" class="form-control" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Plan Tipi *</label>
                        <select id="planType" class="form-control">
                            <option value="sit">SIT — System Integration Test</option>
                            <option value="uat">UAT — User Acceptance Test</option>
                            <option value="regression">Regression</option>
                            <option value="e2e">E2E — End-to-End</option>
                            <option value="cutover_rehearsal">Cutover Rehearsal</option>
                            <option value="performance">Performance</option>
                        </select></div>
                    <div class="form-group"><label>Ortam</label>
                        <select id="planEnv" class="form-control">
                            <option value="">— Seçin —</option>
                            <option value="DEV">DEV</option>
                            <option value="QAS">QAS</option>
                            <option value="PRE">PRE-PROD</option>
                            <option value="PRD">PRD</option>
                        </select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Başlangıç Tarihi</label>
                        <input id="planStart" type="date" class="form-control"></div>
                    <div class="form-group"><label>Bitiş Tarihi</label>
                        <input id="planEnd" type="date" class="form-control"></div>
                </div>
                <div class="form-group"><label>Giriş Kriterleri</label>
                    <textarea id="planEntry" class="form-control" rows="2" placeholder="Test başlamadan önce sağlanması gereken koşullar"></textarea></div>
                <div class="form-group"><label>Çıkış Kriterleri</label>
                    <textarea id="planExit" class="form-control" rows="2" placeholder="Test planını kapatmak için gereken koşullar"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">İptal</button>
                <button class="btn btn-primary" onclick="TestPlanningView.savePlan()">Oluştur</button>
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
        if (!body.name) return App.toast('Plan adı zorunludur', 'error');
        try {
            const created = await API.post(`/programs/${pid}/testing/plans`, body);
            App.toast('Test planı oluşturuldu! Şimdi scope ekleyebilirsiniz.', 'success');
            App.closeModal();
            // Auto-navigate to plan detail so user can add scope
            TestPlanDetailView.open(created.id);
        } catch (e) {
            App.toast(e.message || 'Plan oluşturulamadı', 'error');
        }
    }

    async function deletePlan(id) {
        if (!confirm('Bu test planını ve tüm cycle\'larını silmek istediğinize emin misiniz?')) return;
        await API.delete(`/testing/plans/${id}`);
        App.toast('Test planı silindi', 'success');
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
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📋</div>
                    <div class="empty-state__title">No test cases yet</div>
                    <p>Create your first test case to build the test catalog.</p><br>
                    <button class="btn btn-primary" onclick="TestPlanningView.showCaseModal()">+ New Test Case</button>
                </div>`;
            return;
        }

        const layerBadge = (l) => {
            const colors = { unit: '#0070f3', sit: '#e9730c', uat: '#107e3e', regression: '#a93e7e', e2e: '#6a4fa0', performance: '#6a4fa0', cutover_rehearsal: '#c4314b' };
            return `<span class="badge" style="background:${colors[l] || '#888'};color:#fff">${(l || 'N/A').toUpperCase()}</span>`;
        };
        const statusBadge = (s) => {
            const colors = { draft: '#888', ready: '#0070f3', approved: '#107e3e', in_review: '#e5a800', deprecated: '#c4314b' };
            return `<span class="badge" style="background:${colors[s] || '#888'};color:#fff">${s}</span>`;
        };

        container.innerHTML = `
            <div id="catalogFilterBar" style="margin-bottom:8px"></div>
            <div id="catalogTableArea"></div>
        `;
        renderCatalogFilterBar();
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

        const countEl = document.getElementById('catItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${testCases.length}`;

        const tableEl = document.getElementById('catalogTableArea');
        if (!tableEl) return;
        if (filtered.length === 0) {
            tableEl.innerHTML = '<div class="empty-state" style="padding:40px"><p>No test cases match your filters.</p></div>';
            return;
        }
        tableEl.innerHTML = _renderCatalogTable(filtered);
    }

    // Legacy shim — old server-side filter, now handled client-side
    async function filterCatalog() { applyCatalogFilter(); }

    function _renderCatalogTable(list) {
        const layerBadge = (l) => {
            const colors = { unit: '#0070f3', sit: '#e9730c', uat: '#107e3e', regression: '#a93e7e', e2e: '#6a4fa0', performance: '#6a4fa0', cutover_rehearsal: '#c4314b' };
            return `<span class="badge" style="background:${colors[l] || '#888'};color:#fff">${(l || 'N/A').toUpperCase()}</span>`;
        };
        const statusBadge = (s) => {
            const colors = { draft: '#888', ready: '#0070f3', approved: '#107e3e', in_review: '#e5a800', deprecated: '#c4314b' };
            return `<span class="badge" style="background:${colors[s] || '#888'};color:#fff">${s}</span>`;
        };
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
                        <td><strong>${tc.code || '-'}</strong></td>
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
                <div class="form-group"><label>Title *</label>
                    <input id="tcTitle" class="form-control" value="${isEdit ? tc.title : ''}"></div>
                <div class="form-row">
                    <div class="form-group"><label>Test Layer</label>
                        <select id="tcLayer" class="form-control">
                            ${['unit','sit','uat','e2e','regression','performance','cutover_rehearsal'].map(l =>
                                `<option value="${l}" ${(isEdit && tc.test_layer === l) ? 'selected' : ''}>${l.toUpperCase()}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Module</label>
                        <input id="tcModule" class="form-control" value="${isEdit ? (tc.module || '') : ''}" placeholder="FI, MM, SD..."></div>
                    <div class="form-group"><label>Priority</label>
                        <select id="tcPriority" class="form-control">
                            ${['low','medium','high','critical'].map(p =>
                                `<option value="${p}" ${(isEdit && tc.priority === p) ? 'selected' : ''}>${p}</option>`).join('')}
                        </select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Suite</label>
                        <select id="tcSuiteId" class="form-control">
                            <option value="">— No Suite —</option>
                        </select></div>
                </div>
                <div class="form-group"><label>Description</label>
                    <textarea id="tcDesc" class="form-control" rows="2">${isEdit ? (tc.description || '') : ''}</textarea></div>
                <div class="form-group"><label>Preconditions</label>
                    <textarea id="tcPrecond" class="form-control" rows="2">${isEdit ? (tc.preconditions || '') : ''}</textarea></div>

                <!-- Structured Test Steps -->
                <div class="form-group">
                    <label style="display:flex;justify-content:space-between;align-items:center">
                        <span>Test Steps</span>
                        ${isEdit ? `<button class="btn btn-sm btn-primary" type="button" onclick="TestPlanningView.addStepRow()">+ Add Step</button>` : ''}
                    </label>
                    ${isEdit ? `
                    <div id="stepsContainer" style="margin-top:8px">
                        <div style="text-align:center;padding:12px"><div class="spinner"></div> Loading steps...</div>
                    </div>` : `
                    <textarea id="tcSteps" class="form-control" rows="3" placeholder="Steps will be editable after creation">${''}</textarea>
                    `}
                </div>

                <div class="form-group"><label>Expected Result</label>
                    <textarea id="tcExpected" class="form-control" rows="2">${isEdit ? (tc.expected_result || '') : ''}</textarea></div>
                <div class="form-group"><label>Test Data Set</label>
                    <input id="tcData" class="form-control" value="${isEdit ? (tc.test_data_set || '') : ''}"></div>
                <div class="form-row">
                    <div class="form-group"><label>Assigned To</label>
                        ${assignedHtml}</div>
                    <div class="form-group"><label>
                        <input type="checkbox" id="tcRegression" ${isEdit && tc.is_regression ? 'checked' : ''}> Regression Set</label></div>
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
        _loadSuiteOptions(isEdit ? tc.suite_id : null);

        // Load structured steps for existing cases
        if (isEdit) {
            _loadSteps(tc.id);
            _loadPerfResults(tc.id);
            _loadCaseDependencies(tc.id);
        }
    }

    async function _loadSuiteOptions(selectedSuiteId) {
        const pid = TestingShared.pid;
        try {
            const res = await API.get(`/programs/${pid}/testing/suites?per_page=200`);
            const suites = res.items || res || [];
            const sel = document.getElementById('tcSuiteId');
            if (!sel) return;
            suites.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = `${s.name} (${s.suite_type})`;
                if (selectedSuiteId && s.id === selectedSuiteId) opt.selected = true;
                sel.appendChild(opt);
            });
        } catch (e) {
            console.warn('Could not load suites for selector:', e);
        }
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
        const body = {
            title: document.getElementById('tcTitle').value,
            test_layer: document.getElementById('tcLayer').value,
            module: document.getElementById('tcModule').value,
            priority: document.getElementById('tcPriority').value,
            description: document.getElementById('tcDesc').value,
            preconditions: document.getElementById('tcPrecond').value,
            test_steps: document.getElementById('tcSteps') ? document.getElementById('tcSteps').value : '',
            expected_result: document.getElementById('tcExpected').value,
            test_data_set: document.getElementById('tcData').value,
            assigned_to: document.getElementById('tcAssigned').value,
            assigned_to_id: document.getElementById('tcAssigned').value || null,
            is_regression: document.getElementById('tcRegression').checked,
            suite_id: parseInt(document.getElementById('tcSuiteId').value) || null,
        };
        if (!body.title) return App.toast('Title is required', 'error');

        if (id) {
            await API.put(`/testing/catalog/${id}`, body);
            App.toast('Test case updated', 'success');
        } else {
            await API.post(`/programs/${pid}/testing/catalog`, body);
            App.toast('Test case created', 'success');
        }
        App.closeModal();
        await renderCatalog();
    }

    async function showCaseDetail(id) {
        const tc = await API.get(`/testing/catalog/${id}`);
        showCaseModal(tc);
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
    const SUITE_TYPES = ['SIT', 'UAT', 'Regression', 'E2E', 'Performance', 'Custom'];
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

        const typeBadge = (t) => {
            const colors = { SIT: '#0070f3', UAT: '#107e3e', Regression: '#a93e7e', E2E: '#6a4fa0', Performance: '#e9730c', Custom: '#888' };
            return `<span class="badge" style="background:${colors[t] || '#888'};color:#fff">${t}</span>`;
        };
        const statusBadge = (s) => {
            const colors = { draft: '#888', active: '#0070f3', locked: '#e9730c', archived: '#555' };
            return `<span class="badge" style="background:${colors[s] || '#888'};color:#fff">${s}</span>`;
        };

        container.innerHTML = `
            <div id="suiteFilterBar" style="margin-bottom:8px"></div>
            <div id="suiteTableArea"></div>
        `;
        renderSuiteFilterBar();
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
                    id: 'suite_type', label: 'Type', type: 'multi', color: '#3b82f6',
                    options: SUITE_TYPES.map(t => ({ value: t, label: t })),
                    selected: _suiteFilters.suite_type || [],
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
            filtered = filtered.filter(s => values.includes(String(s[key])));
        });

        const countEl = document.getElementById('suiteItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${testSuites.length}`;

        const tableEl = document.getElementById('suiteTableArea');
        if (!tableEl) return;
        if (filtered.length === 0) {
            tableEl.innerHTML = '<div class="empty-state" style="padding:40px"><p>No suites match your filters.</p></div>';
            return;
        }
        tableEl.innerHTML = _renderSuiteTable(filtered);
    }

    function _renderSuiteTable(list) {
        const typeBadge = (t) => {
            const colors = { SIT: '#0070f3', UAT: '#107e3e', Regression: '#a93e7e', E2E: '#6a4fa0', Performance: '#e9730c', Custom: '#888' };
            return `<span class="badge" style="background:${colors[t] || '#888'};color:#fff">${t}</span>`;
        };
        const statusBadge = (s) => {
            const colors = { draft: '#888', active: '#0070f3', locked: '#e9730c', archived: '#555' };
            return `<span class="badge" style="background:${colors[s] || '#888'};color:#fff">${s}</span>`;
        };
        return `<table class="data-table">
                <thead><tr>
                    <th>Name</th><th>Type</th><th>Status</th><th>Module</th><th>Owner</th><th>Tags</th><th>Actions</th>
                </tr></thead>
                <tbody>
                    ${list.map(s => `<tr onclick="TestPlanningView.showSuiteDetail(${s.id})" style="cursor:pointer" class="clickable-row">
                        <td><strong>${esc(s.name)}</strong></td>
                        <td>${typeBadge(s.suite_type)}</td>
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
                    <div class="form-group"><label>Suite Type</label>
                        <select id="suiteType" class="form-control">
                            ${SUITE_TYPES.map(t =>
                                `<option value="${t}" ${(isEdit && suite.suite_type === t) ? 'selected' : ''}>${t}</option>`).join('')}
                        </select></div>
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
            suite_type: document.getElementById('suiteType').value,
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

        const typeBadge = (t) => {
            const colors = { SIT: '#0070f3', UAT: '#107e3e', Regression: '#a93e7e', E2E: '#6a4fa0', Performance: '#e9730c', Custom: '#888' };
            return `<span class="badge" style="background:${colors[t] || '#888'};color:#fff">${t}</span>`;
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
                    <span>${typeBadge(suite.suite_type)}</span>
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
                                <td><strong>${esc(tc.code || '-')}</strong></td>
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
                            <span><strong>${esc(item.code || '')}</strong> ${esc(item.title)} <span class="badge" style="font-size:10px">${esc(item.type || '')}</span></span>
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
        // Case tabs
        _switchCaseTab, addPerfResult, deletePerfResult,
        addCaseDependency, deleteCaseDependency,
        // Generate
        showGenerateWricefModal, executeGenerateWricef,
        showGenerateProcessModal, executeGenerateProcess,
    };
})();
