/**
 * SAP Transformation Management Platform
 * Test Plan Detail View — TP-Sprint 4 Frontend Integration
 *
 * Provides a 4-tab plan detail view:
 *   1. Scope     — PlanScope items with coverage indicators
 *   2. Test Cases — PlanTestCase pool + suggest/import/manual
 *   3. Data      — PlanDataSet links + readiness check
 *   4. Cycles    — Cycle list + populate + exit criteria
 *
 * Usage: TestPlanDetailView.open(planId)
 * IIFE module — same pattern as other views.
 */

const TestPlanDetailView = (() => {
    'use strict';

    const esc = TestingShared.esc;
    let _planId = null;
    let _plan = null;
    let _currentTab = 'scope';

    // ── Colours ──────────────────────────────────────────────────────
    const STATUS_CLR = { draft: '#888', active: '#0070f3', completed: '#107e3e', cancelled: '#c4314b' };
    const RESULT_CLR = { pass: '#107e3e', fail: '#c4314b', blocked: '#e9730c', not_run: '#888', deferred: '#6a4fa0' };
    const COV_CLR = { covered: '#107e3e', partial: '#e5a800', not_covered: '#c4314b' };
    const COV_LBL = { covered: '✅ Full', partial: '⚠️ Partial', not_covered: '❌ None' };

    // ═══════════════════════════════════════════════════════════════════
    //  ENTRY POINT
    // ═══════════════════════════════════════════════════════════════════

    async function open(planId) {
        _planId = planId;
        _currentTab = 'scope';
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

    function _renderShell() {
        const main = document.getElementById('mainContent');
        const p = _plan;
        const typeBadge = p.plan_type
            ? `<span class="badge" style="background:#0070f3;color:#fff">${esc(p.plan_type).toUpperCase()}</span>` : '';
        const envBadge = p.environment
            ? `<span class="badge" style="background:#6a4fa0;color:#fff">${esc(p.environment)}</span>` : '';

        main.innerHTML = `
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                <button class="btn btn-sm" onclick="TestExecutionView.render()" title="Back to Plans">← Back</button>
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
                            <td><span class="badge badge-priority-${s.priority || 'medium'}">${esc(s.priority || 'medium')}</span></td>
                            <td><span class="badge badge-risk-${s.risk_level || 'medium'}">${esc(s.risk_level || 'medium')}</span></td>
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
                    <select id="scopeType" class="form-control">
                        <option value="requirement">Requirement</option>
                        <option value="l3_process">L3 Process</option>
                        <option value="scenario">Scenario</option>
                    </select></div>
                <div class="form-group"><label>Reference ID *</label>
                    <input id="scopeRefId" class="form-control" placeholder="Entity ID (e.g. 42 or UUID)"></div>
                <div class="form-group"><label>Label *</label>
                    <input id="scopeLabel" class="form-control" placeholder="Human-readable description"></div>
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
                <div class="form-group"><label>Notes</label>
                    <textarea id="scopeNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanDetailView.saveScope()">Add</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveScope() {
        const body = {
            scope_type: document.getElementById('scopeType').value,
            scope_ref_id: document.getElementById('scopeRefId').value,
            scope_label: document.getElementById('scopeLabel').value,
            priority: document.getElementById('scopePriority').value,
            risk_level: document.getElementById('scopeRisk').value,
            notes: document.getElementById('scopeNotes').value,
        };
        if (!body.scope_ref_id || !body.scope_label) return App.toast('Reference ID and Label are required', 'error');
        await API.post(`/testing/plans/${_planId}/scopes`, body);
        App.toast('Scope item added', 'success');
        App.closeModal();
        await _loadTab('scope');
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
                <div style="display:flex;gap:6px">
                    <button class="btn btn-primary btn-sm" onclick="TestPlanDetailView.showAddTCModal()">+ Add Manual</button>
                    <button class="btn btn-sm" style="background:#C08B5C;color:#fff" onclick="TestPlanDetailView.suggestFromScope()">🤖 Suggest from Scope</button>
                    <button class="btn btn-sm" onclick="TestPlanDetailView.showImportSuiteModal()">📥 Import Suite</button>
                </div>
            </div>
            <div style="margin-bottom:8px;color:#666;font-size:13px">
                Total effort: <strong>${totalEffort} min</strong>
            </div>
            ${ptcs.length === 0
                ? '<div class="empty-state"><p>No test cases added yet. Use Suggest, Import, or Add manually.</p></div>'
                : `<table class="data-table">
                    <thead><tr>
                        <th>#</th><th>Code</th><th>Title</th><th>Layer</th><th>Method</th><th>Priority</th><th>Tester</th><th>Effort</th><th>Actions</th>
                    </tr></thead>
                    <tbody>
                        ${ptcs.map((p, i) => `<tr>
                            <td>${p.execution_order || i + 1}</td>
                            <td>${esc(p.test_case_code || '—')}</td>
                            <td>${esc(p.test_case_title || '—')}</td>
                            <td>${esc(p.test_case_type || '—')}</td>
                            <td>${methodBadge(p.added_method)}</td>
                            <td>${esc(p.priority || 'medium')}</td>
                            <td>${esc(p.planned_tester || p.planned_tester_member || '—')}</td>
                            <td>${p.estimated_effort ? p.estimated_effort + ' min' : '—'}</td>
                            <td>
                                <button class="btn btn-sm btn-danger" onclick="TestPlanDetailView.removeTC(${p.id})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
        `;
    }

    function showAddTCModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>Add Test Case to Plan</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Test Case ID *</label>
                    <input id="addTcId" class="form-control" type="number" placeholder="Enter test case ID"></div>
                <div class="form-row">
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
                <div class="form-group"><label>Notes</label>
                    <textarea id="addTcNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanDetailView.saveAddTC()">Add</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveAddTC() {
        const body = {
            test_case_id: parseInt(document.getElementById('addTcId').value),
            priority: document.getElementById('addTcPriority').value,
            estimated_effort: parseInt(document.getElementById('addTcEffort').value) || null,
            notes: document.getElementById('addTcNotes').value,
        };
        if (!body.test_case_id) return App.toast('Test case ID is required', 'error');
        try {
            await API.post(`/testing/plans/${_planId}/test-cases`, body);
            App.toast('Test case added to plan', 'success');
            App.closeModal();
            await _loadTab('test-cases');
        } catch (e) {
            App.toast(e.message || 'Failed to add test case', 'error');
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
            App.toast(result.message || 'No suggestions found. Add scope items first.', 'info');
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
                ${newOnes.length === 0 ? '<p style="color:#999">All suggested TCs are already in the plan.</p>' : `
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
                ${newOnes.length > 0 ? `<button class="btn btn-primary" onclick="TestPlanDetailView._addSelectedSuggestions()">Add Selected (${newOnes.length})</button>` : ''}
            </div>
        `;
        overlay.classList.add('open');
    }

    function _toggleSuggestAll(cb) {
        document.querySelectorAll('.suggest-cb').forEach(c => { c.checked = cb.checked; });
    }

    async function _addSelectedSuggestions() {
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

    function showImportSuiteModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>📥 Import from Suite</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Suite ID *</label>
                    <input id="importSuiteId" class="form-control" type="number" placeholder="Enter test suite ID"></div>
                <p style="color:#666;font-size:13px">All test cases from this suite will be imported into the plan.
                Duplicates are automatically skipped.</p>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanDetailView.executeImportSuite()">Import</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function executeImportSuite() {
        const suiteId = parseInt(document.getElementById('importSuiteId').value);
        if (!suiteId) return App.toast('Suite ID is required', 'error');
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

        const statusIcon = (s) => {
            const map = { ready: '✅', draft: '📝', loading: '⏳', error: '❌' };
            return map[s] || '❓';
        };

        c.innerHTML = `
            <div style="display:flex;justify-content:space-between;margin-bottom:12px">
                <h3 style="margin:0">Linked Data Sets (${pds.length})</h3>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-primary btn-sm" onclick="TestPlanDetailView.showLinkDataSetModal()">🔗 Link Data Set</button>
                    <button class="btn btn-sm" onclick="TestPlanDetailView.checkDataReadiness()">✓ Check Readiness</button>
                </div>
            </div>
            ${pds.length === 0
                ? '<div class="empty-state"><p>No data sets linked. Link data sets from the Data Factory to track test data readiness.</p></div>'
                : `<table class="data-table">
                    <thead><tr>
                        <th>Name</th><th>Environment</th><th>Status</th><th>Mandatory</th><th>Notes</th><th>Actions</th>
                    </tr></thead>
                    <tbody>
                        ${pds.map(d => `<tr>
                            <td>${esc(d.data_set_name || '—')}</td>
                            <td>${esc(d.data_set_environment || '—')}</td>
                            <td>${statusIcon(d.data_set_status)} ${esc(d.data_set_status || '—')}</td>
                            <td>${d.is_mandatory ? '<span style="color:#c4314b;font-weight:600">⚠️ Yes</span>' : 'No'}</td>
                            <td>${esc(d.notes || '—')}</td>
                            <td>
                                <button class="btn btn-sm btn-danger" onclick="TestPlanDetailView.unlinkDataSet(${d.id})">🔗❌</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
        `;
    }

    function showLinkDataSetModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>🔗 Link Data Set</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Data Set ID *</label>
                    <input id="linkDsId" class="form-control" type="number" placeholder="Test data set ID"></div>
                <div class="form-group">
                    <label><input type="checkbox" id="linkDsMandatory" checked> Mandatory for testing</label>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="linkDsNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanDetailView.saveLinkDataSet()">Link</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveLinkDataSet() {
        const body = {
            data_set_id: parseInt(document.getElementById('linkDsId').value),
            is_mandatory: document.getElementById('linkDsMandatory').checked,
            notes: document.getElementById('linkDsNotes').value,
        };
        if (!body.data_set_id) return App.toast('Data set ID is required', 'error');
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
        // Need a cycle to check — use first cycle or plan directly
        const cycles = _plan.cycles || [];
        if (cycles.length === 0) {
            // Fallback: use the data readiness check indirectly
            App.toast('No cycles yet — cannot check data readiness via cycle endpoint', 'info');
            return;
        }
        try {
            const result = await API.get(`/testing/cycles/${cycles[0].id}/data-check`);
            const status = result.all_mandatory_ready ? '✅ All mandatory ready' : '❌ Some mandatory sets NOT ready';
            App.toast(status, result.all_mandatory_ready ? 'success' : 'error');
            // Refresh tab to show latest state
            await _loadTab('data');
        } catch (e) {
            App.toast('Readiness check failed: ' + e.message, 'error');
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  TAB 4: CYCLES
    // ═══════════════════════════════════════════════════════════════════

    async function _renderCyclesTab(c) {
        // Refresh plan to get latest cycles
        _plan = await API.get(`/testing/plans/${_planId}`);
        const cycles = _plan.cycles || [];

        c.innerHTML = `
            <div style="display:flex;justify-content:space-between;margin-bottom:12px">
                <h3 style="margin:0">Test Cycles (${cycles.length})</h3>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.showCycleModal(${_planId})">+ New Cycle</button>
                </div>
            </div>
            ${cycles.length === 0
                ? '<div class="empty-state"><p>No test cycles yet. Create a cycle to start executing tests.</p></div>'
                : `<table class="data-table">
                    <thead><tr>
                        <th>Cycle</th><th>Layer</th><th>Env</th><th>Status</th><th>Start</th><th>End</th><th>Actions</th>
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
                                <button class="btn btn-sm" style="background:#C08B5C;color:#fff" onclick="TestPlanDetailView.populateFromPlan(${cy.id})" title="Populate from plan">📥 Populate</button>
                                <button class="btn btn-sm" onclick="TestPlanDetailView.showCarryForwardModal(${cy.id})" title="Carry forward from another cycle">🔄 Carry Fwd</button>
                                <button class="btn btn-sm" onclick="TestExecutionView.viewCycleExecs(${cy.id})">▶ Executions</button>
                                <button class="btn btn-sm btn-danger" onclick="TestExecutionView.deleteCycle(${cy.id})">🗑</button>
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
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>🔄 Carry Forward</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Source Cycle ID *</label>
                    <input id="cfSourceCycleId" class="form-control" type="number" placeholder="Previous cycle ID"></div>
                <div class="form-group"><label>Filter</label>
                    <select id="cfFilter" class="form-control">
                        <option value="failed_blocked" selected>Failed + Blocked</option>
                        <option value="failed">Failed only</option>
                        <option value="blocked">Blocked only</option>
                        <option value="all">All (carry everything)</option>
                    </select></div>
                <p style="color:#666;font-size:13px">Executions from the source cycle matching the filter will be recreated as "not_run" in this cycle.</p>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestPlanDetailView.executeCarryForward(${cycleId})">Carry Forward</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function executeCarryForward(cycleId) {
        const prevId = parseInt(document.getElementById('cfSourceCycleId').value);
        const filter = document.getElementById('cfFilter').value;
        if (!prevId) return App.toast('Source cycle ID is required', 'error');
        try {
            const result = await API.post(`/testing/cycles/${cycleId}/populate-from-cycle/${prevId}?filter=${filter}`);
            App.toast(`✅ ${result.created} execution(s) carried forward`, 'success');
            App.closeModal();
            await _loadTab('cycles');
        } catch (e) {
            App.toast('Carry forward failed: ' + e.message, 'error');
        }
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
                <span style="color:#107e3e">${summary.full_coverage || 0} full</span>,
                <span style="color:#e5a800">${summary.partial_coverage || 0} partial</span>,
                <span style="color:#c4314b">${summary.no_coverage || 0} none</span>
            </p>
            ${scopes.length === 0
                ? '<div class="empty-state"><p>No scope items to show coverage for.</p></div>'
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
        open,
        switchTab,
        // Scope
        showAddScopeModal, saveScope, deleteScope, refreshCoverage,
        // Test Cases
        showAddTCModal, saveAddTC, removeTC,
        suggestFromScope, _toggleSuggestAll, _addSelectedSuggestions,
        showImportSuiteModal, executeImportSuite,
        // Data
        showLinkDataSetModal, saveLinkDataSet, unlinkDataSet, checkDataReadiness,
        // Cycles
        populateFromPlan, showCarryForwardModal, executeCarryForward,
    };
})();
