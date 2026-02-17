/**
 * SAP Transformation Management Platform
 * Test Plan Detail View — TP-Sprint 4 (Rewrite)
 *
 * 5-tab detail view for a test plan:
 *   1. Scope      — PlanScope items + coverage indicators
 *   2. Test Cases  — PlanTestCase pool + suggest/import/catalog picker
 *   3. Data        — PlanDataSet links + readiness check
 *   4. Cycles      — Cycle list + populate + carry forward
 *   5. Coverage    — Coverage dashboard + exit criteria evaluation
 *
 * Usage: TestPlanDetailView.open(planId, {from: 'planning'|'execution'})
 * IIFE module — same pattern as other views.
 */

const TestPlanDetailView = (() => {
    'use strict';

    const esc = TestingShared.esc;
    let _planId = null;
    let _plan = null;
    let _currentTab = 'scope';
    let _cameFrom = 'planning';   // track navigation source

    // ── Colours ──────────────────────────────────────────────────────
    const STATUS_CLR = { draft: '#888', active: '#0070f3', completed: '#107e3e', cancelled: '#c4314b' };
    const COV_CLR = { covered: '#107e3e', partial: '#e5a800', not_covered: '#c4314b' };
    const COV_LBL = { covered: '✅ Covered', partial: '⚠️ Partial', not_covered: '❌ Not covered' };
    const TYPE_LBL = { sit: 'SIT', uat: 'UAT', regression: 'Regression', e2e: 'E2E', cutover_rehearsal: 'Cutover', performance: 'Performance' };

    // ═══════════════════════════════════════════════════════════════════
    //  ENTRY POINT
    // ═══════════════════════════════════════════════════════════════════

    async function open(planId, opts) {
        _planId = planId;
        _currentTab = 'scope';
        _cameFrom = (opts && opts.from) || 'planning';
        const main = document.getElementById('mainContent');
        main.innerHTML = '<div style="text-align:center;padding:60px"><div class="spinner"></div></div>';

        try {
            _plan = await API.get(`/testing/plans/${planId}`);
        } catch (e) {
            main.innerHTML = `<div class="empty-state"><p>⚠️ Plan not found</p></div>`;
            return;
        }

        _renderShell();
        await _loadTab('scope');
    }

    function _goBack() {
        if (_cameFrom === 'execution') {
            TestExecutionView.render();
        } else {
            TestPlanningView.switchTab('plans');
            TestPlanningView.render();
        }
    }

    function _renderShell() {
        const main = document.getElementById('mainContent');
        const p = _plan;
        const typeBadge = p.plan_type
            ? `<span class="badge" style="background:#0070f3;color:#fff">${TYPE_LBL[p.plan_type] || p.plan_type}</span>` : '';
        const envBadge = p.environment
            ? `<span class="badge" style="background:#6a4fa0;color:#fff">${esc(p.environment)}</span>` : '';

        main.innerHTML = `
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                <button class="btn btn-sm" onclick="TestPlanDetailView._goBack()" title="Back">← Back</button>
                <h1 style="margin:0;font-size:1.4rem">${esc(p.name)}</h1>
                <span class="badge" style="background:${STATUS_CLR[p.status] || '#888'};color:#fff">${esc(p.status)}</span>
                ${typeBadge} ${envBadge}
            </div>
            ${p.description ? `<p style="color:#666;margin:0 0 12px">${esc(p.description)}</p>` : ''}

            <div class="tabs" id="planDetailTabs">
                <div class="tab active" data-tab="scope"      onclick="TestPlanDetailView.switchTab('scope')">📋 Scope</div>
                <div class="tab"        data-tab="test-cases"  onclick="TestPlanDetailView.switchTab('test-cases')">🧪 Test Cases</div>
                <div class="tab"        data-tab="data"        onclick="TestPlanDetailView.switchTab('data')">💾 Data</div>
                <div class="tab"        data-tab="cycles"      onclick="TestPlanDetailView.switchTab('cycles')">🔄 Cycles</div>
                <div class="tab"        data-tab="coverage"    onclick="TestPlanDetailView.switchTab('coverage')">📊 Coverage</div>
            </div>
            <div class="card" id="planDetailContent" style="min-height:200px">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>
        `;
    }

    async function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('#planDetailTabs .tab').forEach(t =>
            t.classList.toggle('active', t.dataset.tab === tab));
        await _loadTab(tab);
    }

    async function _loadTab(tab) {
        const c = document.getElementById('planDetailContent');
        c.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';
        try {
            switch (tab) {
                case 'scope':      await _renderScopeTab(c);     break;
                case 'test-cases': await _renderTCTab(c);        break;
                case 'data':       await _renderDataTab(c);      break;
                case 'cycles':     await _renderCyclesTab(c);    break;
                case 'coverage':   await _renderCoverageTab(c);  break;
            }
        } catch (e) {
            c.innerHTML = `<div class="empty-state"><p>⚠️ ${esc(e.message)}</p></div>`;
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  TAB 1: SCOPE
    // ═══════════════════════════════════════════════════════════════════

    async function _renderScopeTab(c) {
        const res = await API.get(`/testing/plans/${_planId}/scopes`);
        const scopes = res.items || res || [];

        c.innerHTML = `
            <div style="display:flex;justify-content:space-between;margin-bottom:12px">
                <h3 style="margin:0">Scope Items (${scopes.length})</h3>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-primary btn-sm" onclick="TestPlanDetailView.showAddScopeModal()">+ Add Scope</button>
                    <button class="btn btn-sm" onclick="TestPlanDetailView.refreshCoverage()">📊 Refresh Coverage</button>
                </div>
            </div>
            <p style="color:#666;font-size:13px;margin:0 0 12px">
                Define what this plan covers: L3 processes, scenarios, or requirements.
                Scope items drive test case suggestions and coverage tracking.
            </p>
            ${scopes.length === 0
                ? '<div class="empty-state"><p>No scope items defined. Add scope items to define what this plan covers.</p></div>'
                : `<table class="data-table">
                    <thead><tr>
                        <th>Type</th><th>Label</th><th>Priority</th><th>Risk</th><th>Coverage</th><th>Actions</th>
                    </tr></thead>
                    <tbody>
                        ${scopes.map(s => `<tr>
                            <td><span class="badge" style="background:#0070f3;color:#fff">${esc(s.scope_type)}</span></td>
                            <td>${esc(s.scope_label || s.scope_ref_id)}</td>
                            <td>${esc(s.priority || 'medium')}</td>
                            <td>${esc(s.risk_level || 'medium')}</td>
                            <td><span style="color:${COV_CLR[s.coverage_status] || '#888'}">${COV_LBL[s.coverage_status] || s.coverage_status || '—'}</span></td>
                            <td>
                                <button class="btn btn-sm btn-danger" onclick="TestPlanDetailView.deleteScope(${s.id})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
        `;
    }

    function showAddScopeModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>Add Scope Item</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Scope Type *</label>
                    <select id="scopeType" class="form-control" onchange="TestPlanDetailView._onScopeTypeChange()">
                        <option value="requirement">Requirement</option>
                        <option value="l3_process">L3 Process</option>
                        <option value="scenario">Scenario</option>
                    </select></div>
                <div class="form-group"><label>Select or Search</label>
                    <div id="scopePickerArea">
                        <div style="text-align:center;padding:12px"><div class="spinner"></div></div>
                    </div></div>
                <div class="form-group"><label>Label *</label>
                    <input id="scopeLabel" class="form-control" placeholder="Human-readable description"></div>
                <div class="form-group" style="display:none"><label>Reference ID</label>
                    <input id="scopeRefId" class="form-control"></div>
                <div class="form-row">
                    <div class="form-group"><label>Priority</label>
                        <select id="scopePriority" class="form-control">
                            <option value="medium" selected>Medium</option>
                            <option value="low">Low</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </select></div>
                    <div class="form-group"><label>Risk Level</label>
                        <select id="scopeRisk" class="form-control">
                            <option value="medium" selected>Medium</option>
                            <option value="low">Low</option>
                            <option value="high">High</option>
                        </select></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanDetailView.saveScope()">Add</button>
            </div>
        `;
        overlay.classList.add('open');
        _onScopeTypeChange();
    }

    async function _onScopeTypeChange() {
        const scopeType = document.getElementById('scopeType').value;
        const area = document.getElementById('scopePickerArea');
        area.innerHTML = '<div style="text-align:center;padding:12px"><div class="spinner"></div></div>';

        const pid = TestingShared.pid;
        try {
            let items = [];
            if (scopeType === 'requirement') {
                const res = await API.get(`/programs/${pid}/backlog?per_page=200`);
                items = (res.items || res || []).map(r => ({
                    id: r.id, label: `${r.code || ''} — ${r.title}`, type: r.item_type || 'Requirement'
                }));
            } else if (scopeType === 'l3_process') {
                try {
                    const res = await API.get(`/explore/process-levels?project_id=${pid}&per_page=200`);
                    items = (res.items || res || []).map(p => ({
                        id: p.id, label: `${p.level_id || ''} — ${p.name}`, type: `L${p.level || 3}`
                    }));
                } catch(e) { items = []; }
            } else if (scopeType === 'scenario') {
                try {
                    const res = await API.get(`/explore/workshops?project_id=${pid}&per_page=200`);
                    items = (res.items || res || []).map(w => ({
                        id: w.id, label: w.name || w.title, type: 'Scenario'
                    }));
                } catch(e) { items = []; }
            }

            if (items.length === 0) {
                area.innerHTML = `
                    <p style="color:#999;font-size:13px">No ${scopeType.replace('_', ' ')} items found. Enter Reference ID and Label manually below.</p>
                    <input id="scopeRefIdManual" class="form-control" placeholder="Reference ID"
                           onchange="document.getElementById('scopeRefId').value=this.value">`;
                return;
            }

            area.innerHTML = `
                <input type="text" class="form-control" id="scopePickerSearch" placeholder="Search…"
                    oninput="TestPlanDetailView._filterScopePicker()" style="margin-bottom:6px">
                <div id="scopePickerList" style="max-height:180px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:6px">
                    ${items.map(it => `
                        <div class="scope-pick-item" data-id="${it.id}" data-label="${esc(it.label)}"
                             onclick="TestPlanDetailView._selectScopeItem(this)"
                             style="padding:8px 12px;cursor:pointer;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between">
                            <span>${esc(it.label)}</span>
                            <span class="badge" style="background:#eee;color:#666;font-size:11px">${esc(it.type)}</span>
                        </div>`).join('')}
                </div>`;
        } catch (e) {
            area.innerHTML = `<p style="color:#c4314b">Error loading items: ${esc(e.message)}</p>
                <input id="scopeRefIdManual" class="form-control" placeholder="Enter Reference ID manually"
                       onchange="document.getElementById('scopeRefId').value=this.value">`;
        }
    }

    function _filterScopePicker() {
        const q = (document.getElementById('scopePickerSearch')?.value || '').toLowerCase();
        document.querySelectorAll('.scope-pick-item').forEach(el => {
            el.style.display = el.dataset.label.toLowerCase().includes(q) ? '' : 'none';
        });
    }

    function _selectScopeItem(el) {
        document.querySelectorAll('.scope-pick-item').forEach(e => e.style.background = '');
        el.style.background = '#e3f2fd';
        document.getElementById('scopeRefId').value = el.dataset.id;
        const labelInput = document.getElementById('scopeLabel');
        if (!labelInput.value) labelInput.value = el.dataset.label;
    }

    async function saveScope() {
        const body = {
            scope_type: document.getElementById('scopeType').value,
            scope_ref_id: document.getElementById('scopeRefId').value || (document.getElementById('scopeRefIdManual')?.value) || '',
            scope_label: document.getElementById('scopeLabel').value,
            priority: document.getElementById('scopePriority').value,
            risk_level: document.getElementById('scopeRisk').value,
        };
        if (!body.scope_label) return App.toast('Label is required', 'error');
        if (!body.scope_ref_id) return App.toast('Please select or enter a reference', 'error');
        try {
            await API.post(`/testing/plans/${_planId}/scopes`, body);
            App.toast('Scope item added', 'success');
            App.closeModal();
            await _loadTab('scope');
        } catch (e) {
            App.toast(e.message || 'Failed to add scope', 'error');
        }
    }

    async function deleteScope(id) {
        if (!confirm('Remove this scope item?')) return;
        await API.delete(`/testing/plan-scopes/${id}`);
        App.toast('Scope item removed', 'success');
        await _loadTab('scope');
    }

    async function refreshCoverage() {
        App.toast('Calculating coverage…', 'info');
        try {
            await API.get(`/testing/plans/${_planId}/coverage`);
            App.toast('Coverage updated', 'success');
            await _loadTab('scope');
        } catch (e) {
            App.toast('Coverage calculation failed: ' + e.message, 'error');
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  TAB 2: TEST CASES (PlanTestCase pool)
    // ═══════════════════════════════════════════════════════════════════

    async function _renderTCTab(c) {
        const res = await API.get(`/testing/plans/${_planId}/test-cases`);
        const ptcs = res.items || res || [];

        const totalEffort = ptcs.reduce((s, p) => s + (p.estimated_effort || 0), 0);
        const methodBadge = (m) => {
            const clr = { manual: '#888', scope_suggest: '#0070f3', suite_import: '#6a4fa0', ai_suggest: '#e9730c' };
            return `<span class="badge" style="background:${clr[m] || '#888'};color:#fff">${esc(m)}</span>`;
        };

        c.innerHTML = `
            <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <h3 style="margin:0">Test Cases in Plan (${ptcs.length})</h3>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                    <button class="btn btn-primary btn-sm" onclick="TestPlanDetailView.showAddTCModal()">+ Add from Catalog</button>
                    <button class="btn btn-sm" style="background:#C08B5C;color:#fff" onclick="TestPlanDetailView.suggestFromScope()">🤖 Suggest from Scope</button>
                    <button class="btn btn-sm" onclick="TestPlanDetailView.showImportSuiteModal()">📥 Import Suite</button>
                </div>
            </div>
            <div style="margin-bottom:8px;color:#666;font-size:13px">
                Total estimated effort: <strong>${totalEffort} min</strong> (${(totalEffort / 60).toFixed(1)} hrs)
            </div>
            ${ptcs.length === 0
                ? '<div class="empty-state"><p>No test cases added yet. Use Suggest from Scope, Import Suite, or add from Catalog.</p></div>'
                : `<table class="data-table">
                    <thead><tr>
                        <th>#</th><th>Code</th><th>Title</th><th>Layer</th><th>Module</th><th>Method</th><th>Priority</th><th>Tester</th><th>Effort</th><th></th>
                    </tr></thead>
                    <tbody>
                        ${ptcs.map((p, i) => `<tr>
                            <td>${p.execution_order || i + 1}</td>
                            <td><strong>${esc(p.test_case_code || '—')}</strong></td>
                            <td>${esc(p.test_case_title || '—')}</td>
                            <td>${esc((p.test_case_layer || '—').toUpperCase())}</td>
                            <td>${esc(p.test_case_module || '—')}</td>
                            <td>${methodBadge(p.added_method)}</td>
                            <td>${esc(p.priority || 'medium')}</td>
                            <td>${esc(p.planned_tester || p.planned_tester_name || '—')}</td>
                            <td>${p.estimated_effort ? p.estimated_effort + ' min' : '—'}</td>
                            <td>
                                <button class="btn btn-sm btn-danger" onclick="TestPlanDetailView.removeTC(${p.id})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
        `;
    }

    async function showAddTCModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>Add Test Cases to Plan</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <p style="color:#666;font-size:13px;margin-bottom:8px">Select test cases from the catalog to add to this plan.</p>
                <input type="text" class="form-control" id="tcPickerSearch" placeholder="Search by code or title…"
                    oninput="TestPlanDetailView._filterTCPicker()" style="margin-bottom:8px">
                <div id="tcPickerList" style="max-height:300px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:6px">
                    <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
                </div>
                <div class="form-row" style="margin-top:12px">
                    <div class="form-group"><label>Priority</label>
                        <select id="addTcPriority" class="form-control">
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </select></div>
                    <div class="form-group"><label>Estimated Effort (min)</label>
                        <input id="addTcEffort" class="form-control" type="number" placeholder="Minutes"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanDetailView._addSelectedTCs()">Add Selected</button>
            </div>
        `;
        overlay.classList.add('open');
        _loadTCPicker();
    }

    async function _loadTCPicker() {
        const pid = TestingShared.pid;
        const res = await API.get(`/programs/${pid}/testing/catalog`);
        const tcs = res.items || res || [];
        const list = document.getElementById('tcPickerList');
        if (tcs.length === 0) {
            list.innerHTML = '<p style="color:#999;padding:16px;text-align:center">No test cases in catalog. Create test cases first.</p>';
            return;
        }
        const layerClr = { unit: '#0070f3', sit: '#e9730c', uat: '#107e3e', regression: '#a93e7e', e2e: '#6a4fa0' };
        list.innerHTML = tcs.map(tc => `
            <label class="tc-pick-item" data-id="${tc.id}" data-search="${esc((tc.code||'') + ' ' + tc.title).toLowerCase()}"
                   style="display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;border-bottom:1px solid #f0f0f0">
                <input type="checkbox" class="tc-pick-cb" value="${tc.id}">
                <span class="badge" style="background:${layerClr[tc.test_layer]||'#888'};color:#fff;font-size:10px">${(tc.test_layer||'?').toUpperCase()}</span>
                <strong style="min-width:120px">${esc(tc.code || '-')}</strong>
                <span style="flex:1">${esc(tc.title)}</span>
                <span style="color:#999;font-size:11px">${esc(tc.module || '')}</span>
            </label>`).join('');
    }

    function _filterTCPicker() {
        const q = (document.getElementById('tcPickerSearch')?.value || '').toLowerCase();
        document.querySelectorAll('.tc-pick-item').forEach(el => {
            el.style.display = el.dataset.search.includes(q) ? '' : 'none';
        });
    }

    async function _addSelectedTCs() {
        const ids = [...document.querySelectorAll('.tc-pick-cb:checked')].map(c => parseInt(c.value));
        if (ids.length === 0) return App.toast('Select at least one test case', 'error');
        try {
            await API.post(`/testing/plans/${_planId}/test-cases/bulk`, { test_case_ids: ids });
            App.toast(`${ids.length} test case(s) added to plan`, 'success');
            App.closeModal();
            await _loadTab('test-cases');
        } catch (e) {
            App.toast(e.message || 'Failed to add test cases', 'error');
        }
    }

    async function removeTC(ptcId) {
        if (!confirm('Remove this test case from the plan?')) return;
        await API.delete(`/testing/plan-test-cases/${ptcId}`);
        App.toast('Test case removed', 'success');
        await _loadTab('test-cases');
    }

    async function suggestFromScope() {
        App.toast('Analyzing scope for suggestions…', 'info');
        try {
            const result = await API.post(`/testing/plans/${_planId}/suggest-test-cases`);
            _openSuggestionsModal(result);
        } catch (e) {
            App.toast('Suggestion failed: ' + e.message, 'error');
        }
    }

    function _openSuggestionsModal(result) {
        const suggestions = result.suggestions || [];
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');

        if (suggestions.length === 0) {
            App.toast(result.message || 'No suggestions found. Add scope items first, and ensure test cases are linked to requirements/processes.', 'info');
            return;
        }

        const newOnes = suggestions.filter(s => !s.already_in_plan);
        modal.innerHTML = `
            <div class="modal-header"><h2>🤖 Suggested Test Cases (${result.total})</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body" style="max-height:60vh;overflow-y:auto">
                <p style="margin-bottom:8px">
                    <strong>${result.new}</strong> new suggestions, <strong>${result.already_in_plan}</strong> already in plan.
                </p>
                ${newOnes.length === 0 ? '<p style="color:#999">All suggested test cases are already in the plan.</p>' : `
                <table class="data-table">
                    <thead><tr>
                        <th><input type="checkbox" id="suggestSelectAll" onchange="TestPlanDetailView._toggleSuggestAll(this)" checked></th>
                        <th>Code</th><th>Title</th><th>Layer</th><th>Reason</th>
                    </tr></thead>
                    <tbody>
                        ${newOnes.map(s => `<tr>
                            <td><input type="checkbox" class="suggest-cb" value="${s.test_case_id}" checked></td>
                            <td>${esc(s.code || '—')}</td>
                            <td>${esc(s.title)}</td>
                            <td>${esc(s.test_layer || '—')}</td>
                            <td style="font-size:12px;color:#666">${esc(s.reason)}</td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                ${newOnes.length > 0 ? `<button class="btn btn-primary" onclick="TestPlanDetailView._addSuggestedTCs()">Add Selected (${newOnes.length})</button>` : ''}
            </div>
        `;
        overlay.classList.add('open');
    }

    function _toggleSuggestAll(cb) {
        document.querySelectorAll('.suggest-cb').forEach(c => { c.checked = cb.checked; });
    }

    async function _addSuggestedTCs() {
        const ids = [...document.querySelectorAll('.suggest-cb:checked')].map(c => parseInt(c.value));
        if (ids.length === 0) return App.toast('Select at least one test case', 'error');
        try {
            await API.post(`/testing/plans/${_planId}/test-cases/bulk`, { test_case_ids: ids });
            App.toast(`${ids.length} test case(s) added to plan`, 'success');
            App.closeModal();
            await _loadTab('test-cases');
        } catch (e) {
            App.toast(e.message || 'Bulk add failed', 'error');
        }
    }

    async function showImportSuiteModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>📥 Import from Suite</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <p style="color:#666;font-size:13px;margin-bottom:8px">Select a test suite to import all its test cases into this plan.</p>
                <div id="suitePickerList" style="max-height:300px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:6px">
                    <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
                </div>
                <p style="color:#666;font-size:12px;margin-top:8px">Duplicates are automatically skipped.</p>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
            </div>
        `;
        overlay.classList.add('open');
        _loadSuitePicker();
    }

    async function _loadSuitePicker() {
        const pid = TestingShared.pid;
        const res = await API.get(`/programs/${pid}/testing/suites?per_page=200`);
        const suites = res.items || res || [];
        const list = document.getElementById('suitePickerList');
        if (suites.length === 0) {
            list.innerHTML = '<p style="color:#999;padding:16px;text-align:center">No test suites available. Create suites in Test Planning first.</p>';
            return;
        }
        list.innerHTML = suites.map(s => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-bottom:1px solid #f0f0f0">
                <div>
                    <strong>${esc(s.name)}</strong>
                    <span class="badge" style="background:#eee;color:#666;margin-left:6px">${esc(s.suite_type || 'general')}</span>
                    ${s.module ? `<span style="color:#999;font-size:12px;margin-left:6px">${esc(s.module)}</span>` : ''}
                </div>
                <button class="btn btn-primary btn-sm" onclick="TestPlanDetailView.executeImportSuite(${s.id})">Import</button>
            </div>`).join('');
    }

    async function executeImportSuite(suiteId) {
        try {
            const result = await API.post(`/testing/plans/${_planId}/import-suite/${suiteId}`);
            App.toast(`Imported: ${result.added} added, ${result.skipped} skipped (${result.suite_name})`, 'success');
            App.closeModal();
            await _loadTab('test-cases');
        } catch (e) {
            App.toast(e.message || 'Import failed', 'error');
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  TAB 3: DATA SETS
    // ═══════════════════════════════════════════════════════════════════

    async function _renderDataTab(c) {
        const res = await API.get(`/testing/plans/${_planId}/data-sets`);
        const pds = res.items || res || [];

        c.innerHTML = `
            <div style="display:flex;justify-content:space-between;margin-bottom:12px">
                <h3 style="margin:0">Linked Data Sets (${pds.length})</h3>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-primary btn-sm" onclick="TestPlanDetailView.showLinkDataSetModal()">🔗 Link Data Set</button>
                    <button class="btn btn-sm" onclick="TestPlanDetailView.checkDataReadiness()">✓ Check Readiness</button>
                </div>
            </div>
            <p style="color:#666;font-size:13px;margin:0 0 12px">
                Link data sets from the Data Factory to track test data readiness for this plan.
            </p>
            ${pds.length === 0
                ? '<div class="empty-state"><p>No data sets linked. Link data sets from the Data Factory to track test data readiness.</p></div>'
                : `<table class="data-table">
                    <thead><tr>
                        <th>Name</th><th>Environment</th><th>Status</th><th>Mandatory</th><th>Notes</th><th></th>
                    </tr></thead>
                    <tbody>
                        ${pds.map(d => `<tr>
                            <td><strong>${esc(d.data_set_name || 'Data Set #' + d.data_set_id)}</strong></td>
                            <td>${esc(d.data_set_environment || '—')}</td>
                            <td>${esc(d.data_set_status || '—')}</td>
                            <td>${d.is_mandatory ? '<span style="color:#c4314b;font-weight:600">⚠️ Required</span>' : 'Optional'}</td>
                            <td>${esc(d.notes || '—')}</td>
                            <td>
                                <button class="btn btn-sm btn-danger" onclick="TestPlanDetailView.unlinkDataSet(${d.id})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
        `;
    }

    async function showLinkDataSetModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>🔗 Link Data Set</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <p style="color:#666;font-size:13px;margin-bottom:8px">Select a data set from the Data Factory.</p>
                <div id="dsPickerList" style="max-height:250px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:6px">
                    <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
                </div>
                <div class="form-group" style="margin-top:12px">
                    <label><input type="checkbox" id="linkDsMandatory" checked> Mandatory for testing</label>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="linkDsNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
            </div>
        `;
        overlay.classList.add('open');
        _loadDataSetPicker();
    }

    async function _loadDataSetPicker() {
        const pid = TestingShared.pid;
        const list = document.getElementById('dsPickerList');
        try {
            const res = await API.get(`/programs/${pid}/data-factory/datasets?per_page=200`);
            const datasets = res.items || res || [];
            if (datasets.length === 0) {
                list.innerHTML = '<p style="color:#999;padding:16px;text-align:center">No data sets found in Data Factory.</p>';
                return;
            }
            list.innerHTML = datasets.map(ds => `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-bottom:1px solid #f0f0f0">
                    <div>
                        <strong>${esc(ds.name)}</strong>
                        <span style="color:#999;font-size:12px;margin-left:6px">${esc(ds.environment || '')}</span>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="TestPlanDetailView._linkDataSet(${ds.id})">Link</button>
                </div>`).join('');
        } catch(e) {
            list.innerHTML = `<p style="color:#c4314b;padding:12px">Could not load data sets. Enter ID manually:</p>
                <input id="manualDsId" type="number" class="form-control" placeholder="Data Set ID">
                <button class="btn btn-primary btn-sm" style="margin-top:6px" onclick="TestPlanDetailView._linkDataSet(parseInt(document.getElementById('manualDsId').value))">Link</button>`;
        }
    }

    async function _linkDataSet(dsId) {
        if (!dsId) return App.toast('Please select a data set', 'error');
        const body = {
            data_set_id: dsId,
            is_mandatory: document.getElementById('linkDsMandatory')?.checked ?? true,
            notes: document.getElementById('linkDsNotes')?.value || '',
        };
        try {
            await API.post(`/testing/plans/${_planId}/data-sets`, body);
            App.toast('Data set linked', 'success');
            App.closeModal();
            await _loadTab('data');
        } catch (e) {
            App.toast(e.message || 'Link failed', 'error');
        }
    }

    async function unlinkDataSet(pdsId) {
        if (!confirm('Unlink this data set from the plan?')) return;
        await API.delete(`/testing/plan-data-sets/${pdsId}`);
        App.toast('Data set unlinked', 'success');
        await _loadTab('data');
    }

    async function checkDataReadiness() {
        const cycles = _plan.cycles || [];
        if (cycles.length === 0) {
            App.toast('No cycles yet — create a cycle first to check data readiness', 'info');
            return;
        }
        try {
            const result = await API.get(`/testing/cycles/${cycles[0].id}/data-check`);
            const status = result.all_mandatory_ready ? '✅ All mandatory data sets ready' : '❌ Some mandatory data sets are NOT ready';
            App.toast(status, result.all_mandatory_ready ? 'success' : 'error');
            await _loadTab('data');
        } catch (e) {
            App.toast('Readiness check failed: ' + e.message, 'error');
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  TAB 4: CYCLES
    // ═══════════════════════════════════════════════════════════════════

    async function _renderCyclesTab(c) {
        _plan = await API.get(`/testing/plans/${_planId}`);
        const cycles = _plan.cycles || [];

        c.innerHTML = `
            <div style="display:flex;justify-content:space-between;margin-bottom:12px">
                <h3 style="margin:0">Test Cycles (${cycles.length})</h3>
                <button class="btn btn-primary btn-sm" onclick="TestExecutionView.showCycleModal(${_planId})">+ New Cycle</button>
            </div>
            <p style="color:#666;font-size:13px;margin:0 0 12px">
                Create cycles, then populate them with test cases from the plan. Each cycle represents a round of testing.
            </p>
            ${cycles.length === 0
                ? '<div class="empty-state"><p>No test cycles yet. Create a cycle to start executing tests.</p></div>'
                : `<table class="data-table">
                    <thead><tr>
                        <th>Cycle</th><th>Layer</th><th>Environment</th><th>Status</th><th>Start</th><th>End</th><th>Actions</th>
                    </tr></thead>
                    <tbody>
                        ${cycles.map(cy => `<tr>
                            <td><strong>${esc(cy.name)}</strong></td>
                            <td>${esc((cy.test_layer || '—').toUpperCase())}</td>
                            <td>${esc(cy.environment || '—')}</td>
                            <td><span class="badge" style="background:${STATUS_CLR[cy.status] || '#888'};color:#fff">${esc(cy.status)}</span></td>
                            <td>${cy.start_date || '—'}</td>
                            <td>${cy.end_date || '—'}</td>
                            <td style="display:flex;gap:4px;flex-wrap:wrap">
                                <button class="btn btn-sm" style="background:#C08B5C;color:#fff" onclick="TestPlanDetailView.populateFromPlan(${cy.id})" title="Create executions from plan TCs">📥 Populate</button>
                                <button class="btn btn-sm" onclick="TestPlanDetailView.showCarryForwardModal(${cy.id})" title="Re-run failed/blocked from another cycle">🔄 Carry Fwd</button>
                                <button class="btn btn-sm" onclick="TestExecutionView.viewCycleExecs(${cy.id})">▶ Executions</button>
                                <button class="btn btn-sm btn-danger" onclick="TestPlanDetailView._deleteCycle(${cy.id})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
        `;
    }

    async function populateFromPlan(cycleId) {
        if (!confirm('Populate this cycle from the test plan? Execution records will be created for all planned test cases.')) return;
        try {
            const result = await API.post(`/testing/cycles/${cycleId}/populate`);
            App.toast(`✅ ${result.created} execution(s) created`, 'success');
            await _loadTab('cycles');
        } catch (e) {
            App.toast('Populate failed: ' + e.message, 'error');
        }
    }

    function showCarryForwardModal(cycleId) {
        const cycles = _plan.cycles || [];
        const otherCycles = cycles.filter(cy => cy.id !== cycleId);

        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>🔄 Carry Forward</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <p style="color:#666;font-size:13px;margin-bottom:8px">
                    Re-run failed or blocked executions from a previous cycle into this one.
                </p>
                <div class="form-group"><label>Source Cycle *</label>
                    ${otherCycles.length > 0 ? `
                        <select id="cfSourceCycleId" class="form-control">
                            ${otherCycles.map(cy => `<option value="${cy.id}">${esc(cy.name)} (${esc(cy.status)})</option>`).join('')}
                        </select>` : `
                        <input id="cfSourceCycleId" class="form-control" type="number" placeholder="Source cycle ID (no other cycles in this plan)">`}
                </div>
                <div class="form-group"><label>Filter</label>
                    <select id="cfFilter" class="form-control">
                        <option value="failed_blocked" selected>Failed + Blocked</option>
                        <option value="failed">Failed only</option>
                        <option value="blocked">Blocked only</option>
                        <option value="all">All (carry everything)</option>
                    </select></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanDetailView.executeCarryForward(${cycleId})">Carry Forward</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function executeCarryForward(cycleId) {
        const srcEl = document.getElementById('cfSourceCycleId');
        const prevId = parseInt(srcEl.value);
        const filter = document.getElementById('cfFilter').value;
        if (!prevId) return App.toast('Source cycle is required', 'error');
        try {
            const result = await API.post(`/testing/cycles/${cycleId}/populate-from-cycle/${prevId}?filter=${filter}`);
            App.toast(`✅ ${result.created} execution(s) carried forward`, 'success');
            App.closeModal();
            await _loadTab('cycles');
        } catch (e) {
            App.toast('Carry forward failed: ' + e.message, 'error');
        }
    }

    async function _deleteCycle(cycleId) {
        if (!confirm('Delete this cycle and all its executions?')) return;
        await API.delete(`/testing/cycles/${cycleId}`);
        App.toast('Cycle deleted', 'success');
        await _loadTab('cycles');
    }

    // ═══════════════════════════════════════════════════════════════════
    //  TAB 5: COVERAGE DASHBOARD
    // ═══════════════════════════════════════════════════════════════════

    async function _renderCoverageTab(c) {
        let coverageData, exitData;
        try {
            [coverageData, exitData] = await Promise.all([
                API.get(`/testing/plans/${_planId}/coverage`),
                API.post(`/testing/plans/${_planId}/evaluate-exit`),
            ]);
        } catch (e) {
            c.innerHTML = `<div class="empty-state"><p>⚠️ ${esc(e.message)}</p></div>`;
            return;
        }

        const scopes = coverageData.scopes || [];
        const summary = coverageData.summary || {};
        const gates = exitData.gates || [];
        const stats = exitData.stats || {};

        c.innerHTML = `
            <!-- Exit Criteria Gates -->
            <div style="margin-bottom:20px">
                <h3 style="margin:0 0 8px">
                    Exit Criteria: <span style="color:${exitData.overall === 'PASS' ? '#107e3e' : '#c4314b'}; font-size:1.2em">
                        ${exitData.overall === 'PASS' ? '✅ PASS' : '❌ FAIL'}
                    </span>
                </h3>
                <div style="display:flex;gap:12px;flex-wrap:wrap">
                    ${gates.map(g => `
                        <div style="background:${g.passed ? '#e8f5e9' : '#ffeaea'};border:1px solid ${g.passed ? '#c8e6c9' : '#ffcdd2'};border-radius:8px;padding:10px 16px;min-width:140px">
                            <div style="font-size:18px;font-weight:700;color:${g.passed ? '#107e3e' : '#c4314b'}">${g.passed ? '✅' : '❌'} ${esc(g.value)}</div>
                            <div style="font-size:12px;color:#666">${esc(g.name)}</div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Execution Stats -->
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
                <div class="kpi-card" style="min-width:100px">
                    <div class="kpi-card__value">${stats.total_executions || 0}</div>
                    <div class="kpi-card__label">Total</div>
                </div>
                <div class="kpi-card" style="min-width:100px;border-left:3px solid #107e3e">
                    <div class="kpi-card__value" style="color:#107e3e">${stats.passed || 0}</div>
                    <div class="kpi-card__label">Passed</div>
                </div>
                <div class="kpi-card" style="min-width:100px;border-left:3px solid #c4314b">
                    <div class="kpi-card__value" style="color:#c4314b">${stats.failed || 0}</div>
                    <div class="kpi-card__label">Failed</div>
                </div>
                <div class="kpi-card" style="min-width:100px;border-left:3px solid #e9730c">
                    <div class="kpi-card__value" style="color:#e9730c">${stats.blocked || 0}</div>
                    <div class="kpi-card__label">Blocked</div>
                </div>
                <div class="kpi-card" style="min-width:100px;border-left:3px solid #888">
                    <div class="kpi-card__value">${stats.not_run || 0}</div>
                    <div class="kpi-card__label">Not Run</div>
                </div>
            </div>

            <!-- Scope Coverage Matrix -->
            <h3 style="margin:0 0 8px">Scope Coverage Matrix</h3>
            <p style="color:#666;font-size:13px;margin-bottom:8px">
                ${summary.total_scopes || 0} scopes:
                <span style="color:#107e3e">${summary.full_coverage || 0} covered</span>,
                <span style="color:#e5a800">${summary.partial_coverage || 0} partial</span>,
                <span style="color:#c4314b">${summary.no_coverage || 0} none</span>
            </p>
            ${scopes.length === 0
                ? '<div class="empty-state"><p>No scope items to show coverage for. Add scope items first.</p></div>'
                : `<table class="data-table">
                    <thead><tr>
                        <th>Scope</th><th>Type</th><th>Traceable</th><th>In Plan</th><th>Executed</th><th>Passed</th><th>Coverage</th><th>Execution</th><th>Pass Rate</th>
                    </tr></thead>
                    <tbody>
                        ${scopes.map(s => `<tr>
                            <td>${esc(s.scope_label || s.scope_ref_id)}</td>
                            <td>${esc(s.scope_type)}</td>
                            <td>${s.total_traceable_tcs}</td>
                            <td>${s.in_plan}</td>
                            <td>${s.executed}</td>
                            <td>${s.passed}</td>
                            <td>${_progressBar(s.coverage_pct)}</td>
                            <td>${_progressBar(s.execution_pct)}</td>
                            <td>${_progressBar(s.pass_rate)}</td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
        `;
    }

    function _progressBar(pct) {
        const p = pct || 0;
        const color = p >= 95 ? '#107e3e' : p >= 70 ? '#e5a800' : '#c4314b';
        return `
            <div style="display:flex;align-items:center;gap:6px">
                <div style="flex:1;background:#eee;border-radius:4px;height:8px;min-width:60px">
                    <div style="width:${Math.min(p, 100)}%;background:${color};height:100%;border-radius:4px"></div>
                </div>
                <span style="font-size:12px;color:${color};min-width:38px;text-align:right">${p}%</span>
            </div>
        `;
    }

    // ═══════════════════════════════════════════════════════════════════
    //  PUBLIC API
    // ═══════════════════════════════════════════════════════════════════

    return {
        open, switchTab, _goBack,
        // Scope
        showAddScopeModal, saveScope, deleteScope, refreshCoverage,
        _onScopeTypeChange, _filterScopePicker, _selectScopeItem,
        // Test Cases
        showAddTCModal, _filterTCPicker, _addSelectedTCs, removeTC,
        suggestFromScope, _toggleSuggestAll, _addSuggestedTCs,
        showImportSuiteModal, executeImportSuite,
        // Data
        showLinkDataSetModal, _linkDataSet, unlinkDataSet, checkDataReadiness,
        // Cycles
        populateFromPlan, showCarryForwardModal, executeCarryForward, _deleteCycle,
    };
})();
