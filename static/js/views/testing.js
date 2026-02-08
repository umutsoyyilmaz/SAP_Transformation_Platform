/**
 * SAP Transformation Management Platform
 * Test Hub View — Sprint 5: Test Catalog, Execution, Defect Management & KPI Dashboard.
 *
 * Tabs: Catalog | Executions | Defects | Traceability | Dashboard
 */

const TestingView = (() => {
    let programs = [];
    let selectedProgramId = null;
    let currentTab = 'catalog';

    // State
    let testCases = [];
    let testPlans = [];
    let defects = [];
    let dashboardData = null;

    // ── Main render ───────────────────────────────────────────────────────
    async function render() {
        const prog = App.getActiveProgram();
        selectedProgramId = prog ? prog.id : null;
        const main = document.getElementById('mainContent');

        if (!selectedProgramId) {
            main.innerHTML = `
                <div class="page-header"><h1>🧪 Test Hub</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">🧪</div>
                    <div class="empty-state__title">Select a Program</div>
                    <p>Go to <a href="#" onclick="App.navigate('programs');return false">Programs</a> to select one.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>🧪 Test Hub</h1>
            </div>
            <div class="tabs" id="testTabs">
                <div class="tab active" data-tab="catalog" onclick="TestingView.switchTab('catalog')">📋 Catalog</div>
                <div class="tab" data-tab="plans" onclick="TestingView.switchTab('plans')">📅 Plans & Cycles</div>
                <div class="tab" data-tab="defects" onclick="TestingView.switchTab('defects')">🐛 Defects</div>
                <div class="tab" data-tab="traceability" onclick="TestingView.switchTab('traceability')">🔗 Traceability</div>
                <div class="tab" data-tab="dashboard" onclick="TestingView.switchTab('dashboard')">📊 Dashboard</div>
            </div>
            <div class="card" id="testContent">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>
        `;
        await loadTabData();
    }

    async function onProgramChange() {
        const prog = App.getActiveProgram();
        selectedProgramId = prog ? prog.id : null;
        if (selectedProgramId) {
            await loadTabData();
        }
    }

    function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('#testTabs .tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        if (selectedProgramId) loadTabData();
    }

    async function loadTabData() {
        const container = document.getElementById('testContent');
        container.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';
        try {
            switch (currentTab) {
                case 'catalog': await renderCatalog(); break;
                case 'plans': await renderPlans(); break;
                case 'defects': await renderDefects(); break;
                case 'traceability': await renderTraceability(); break;
                case 'dashboard': await renderDashboard(); break;
            }
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // CATALOG TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderCatalog() {
        testCases = await API.get(`/programs/${selectedProgramId}/testing/catalog`);
        const container = document.getElementById('testContent');

        if (testCases.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📋</div>
                    <div class="empty-state__title">No test cases yet</div>
                    <p>Create your first test case to build the test catalog.</p><br>
                    <button class="btn btn-primary" onclick="TestingView.showCaseModal()">+ New Test Case</button>
                </div>`;
            return;
        }

        const layerBadge = (l) => {
            const colors = { unit: '#0070f3', sit: '#e9730c', uat: '#107e3e', regression: '#a93e7e', performance: '#6a4fa0', cutover_rehearsal: '#c4314b' };
            return `<span class="badge" style="background:${colors[l] || '#888'};color:#fff">${(l || 'N/A').toUpperCase()}</span>`;
        };
        const statusBadge = (s) => {
            const colors = { draft: '#888', ready: '#0070f3', approved: '#107e3e', deprecated: '#c4314b' };
            return `<span class="badge" style="background:${colors[s] || '#888'};color:#fff">${s}</span>`;
        };

        container.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                <div style="display:flex;gap:8px">
                    <select id="filterLayer" class="form-control" style="width:140px" onchange="TestingView.filterCatalog()">
                        <option value="">All Layers</option>
                        <option value="unit">Unit</option><option value="sit">SIT</option>
                        <option value="uat">UAT</option><option value="regression">Regression</option>
                        <option value="performance">Performance</option><option value="cutover_rehearsal">Cutover</option>
                    </select>
                    <select id="filterCaseStatus" class="form-control" style="width:130px" onchange="TestingView.filterCatalog()">
                        <option value="">All Status</option>
                        <option value="draft">Draft</option><option value="ready">Ready</option>
                        <option value="approved">Approved</option><option value="deprecated">Deprecated</option>
                    </select>
                    <input id="filterCaseSearch" class="form-control" style="width:200px" placeholder="Search..." oninput="TestingView.filterCatalog()">
                </div>
                <button class="btn btn-primary" onclick="TestingView.showCaseModal()">+ New Test Case</button>
            </div>
            <table class="data-table">
                <thead><tr>
                    <th>Code</th><th>Title</th><th>Layer</th><th>Module</th><th>Status</th>
                    <th>Priority</th><th>Regression</th><th>Actions</th>
                </tr></thead>
                <tbody id="catalogBody">
                    ${testCases.map(tc => `<tr>
                        <td><strong>${tc.code || '-'}</strong></td>
                        <td>${tc.title}</td>
                        <td>${layerBadge(tc.test_layer)}</td>
                        <td>${tc.module || '-'}</td>
                        <td>${statusBadge(tc.status)}</td>
                        <td>${tc.priority}</td>
                        <td>${tc.is_regression ? '✅' : '-'}</td>
                        <td>
                            <button class="btn btn-sm" onclick="TestingView.showCaseDetail(${tc.id})">View</button>
                            <button class="btn btn-sm btn-danger" onclick="TestingView.deleteCase(${tc.id})">🗑</button>
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>
            <div style="margin-top:8px;color:#666;font-size:13px">${testCases.length} test case(s)</div>
        `;
    }

    async function filterCatalog() {
        const layer = document.getElementById('filterLayer').value;
        const status = document.getElementById('filterCaseStatus').value;
        const search = document.getElementById('filterCaseSearch').value;
        let params = [];
        if (layer) params.push(`test_layer=${layer}`);
        if (status) params.push(`status=${status}`);
        if (search) params.push(`search=${encodeURIComponent(search)}`);
        const qs = params.length ? '?' + params.join('&') : '';
        testCases = await API.get(`/programs/${selectedProgramId}/testing/catalog${qs}`);
        await renderCatalog();
    }

    function showCaseModal(tc = null) {
        const isEdit = !!tc;
        const title = isEdit ? 'Edit Test Case' : 'New Test Case';
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Title *</label>
                    <input id="tcTitle" class="form-control" value="${isEdit ? tc.title : ''}"></div>
                <div class="form-row">
                    <div class="form-group"><label>Test Layer</label>
                        <select id="tcLayer" class="form-control">
                            ${['unit','sit','uat','regression','performance','cutover_rehearsal'].map(l =>
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
                <div class="form-group"><label>Description</label>
                    <textarea id="tcDesc" class="form-control" rows="2">${isEdit ? (tc.description || '') : ''}</textarea></div>
                <div class="form-group"><label>Preconditions</label>
                    <textarea id="tcPrecond" class="form-control" rows="2">${isEdit ? (tc.preconditions || '') : ''}</textarea></div>
                <div class="form-group"><label>Test Steps</label>
                    <textarea id="tcSteps" class="form-control" rows="3">${isEdit ? (tc.test_steps || '') : ''}</textarea></div>
                <div class="form-group"><label>Expected Result</label>
                    <textarea id="tcExpected" class="form-control" rows="2">${isEdit ? (tc.expected_result || '') : ''}</textarea></div>
                <div class="form-group"><label>Test Data Set</label>
                    <input id="tcData" class="form-control" value="${isEdit ? (tc.test_data_set || '') : ''}"></div>
                <div class="form-row">
                    <div class="form-group"><label>Assigned To</label>
                        <input id="tcAssigned" class="form-control" value="${isEdit ? (tc.assigned_to || '') : ''}"></div>
                    <div class="form-group"><label>
                        <input type="checkbox" id="tcRegression" ${isEdit && tc.is_regression ? 'checked' : ''}> Regression Set</label></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestingView.saveCase(${isEdit ? tc.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveCase(id) {
        const body = {
            title: document.getElementById('tcTitle').value,
            test_layer: document.getElementById('tcLayer').value,
            module: document.getElementById('tcModule').value,
            priority: document.getElementById('tcPriority').value,
            description: document.getElementById('tcDesc').value,
            preconditions: document.getElementById('tcPrecond').value,
            test_steps: document.getElementById('tcSteps').value,
            expected_result: document.getElementById('tcExpected').value,
            test_data_set: document.getElementById('tcData').value,
            assigned_to: document.getElementById('tcAssigned').value,
            is_regression: document.getElementById('tcRegression').checked,
        };
        if (!body.title) return App.toast('Title is required', 'error');

        if (id) {
            await API.put(`/testing/catalog/${id}`, body);
            App.toast('Test case updated', 'success');
        } else {
            await API.post(`/programs/${selectedProgramId}/testing/catalog`, body);
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
    // PLANS & CYCLES TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderPlans() {
        testPlans = await API.get(`/programs/${selectedProgramId}/testing/plans`);
        const container = document.getElementById('testContent');

        if (testPlans.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📅</div>
                    <div class="empty-state__title">No test plans yet</div>
                    <p>Create a test plan to organize test cycles.</p><br>
                    <button class="btn btn-primary" onclick="TestingView.showPlanModal()">+ New Test Plan</button>
                </div>`;
            return;
        }

        let html = `
            <div style="display:flex;justify-content:space-between;margin-bottom:16px">
                <h3 style="margin:0">Test Plans</h3>
                <button class="btn btn-primary" onclick="TestingView.showPlanModal()">+ New Test Plan</button>
            </div>`;

        for (const plan of testPlans) {
            const detail = await API.get(`/testing/plans/${plan.id}`);
            const statusColor = { draft: '#888', active: '#0070f3', completed: '#107e3e', cancelled: '#c4314b' };
            html += `
                <div class="card" style="margin-bottom:12px;padding:16px;border-left:4px solid ${statusColor[plan.status] || '#888'}">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <strong>${plan.name}</strong>
                            <span class="badge" style="background:${statusColor[plan.status] || '#888'};color:#fff;margin-left:8px">${plan.status}</span>
                        </div>
                        <div style="display:flex;gap:6px">
                            <button class="btn btn-sm" onclick="TestingView.showCycleModal(${plan.id})">+ Cycle</button>
                            <button class="btn btn-sm btn-danger" onclick="TestingView.deletePlan(${plan.id})">🗑</button>
                        </div>
                    </div>
                    ${plan.description ? `<p style="color:#666;margin:4px 0">${plan.description}</p>` : ''}
                    ${detail.cycles && detail.cycles.length > 0 ? `
                        <table class="data-table" style="margin-top:10px">
                            <thead><tr><th>Cycle</th><th>Layer</th><th>Status</th><th>Start</th><th>End</th><th>Actions</th></tr></thead>
                            <tbody>
                                ${detail.cycles.map(c => `<tr>
                                    <td><strong>${c.name}</strong></td>
                                    <td>${(c.test_layer || '-').toUpperCase()}</td>
                                    <td><span class="badge">${c.status}</span></td>
                                    <td>${c.start_date || '-'}</td>
                                    <td>${c.end_date || '-'}</td>
                                    <td>
                                        <button class="btn btn-sm" onclick="TestingView.viewCycleExecs(${c.id})">Executions</button>
                                        <button class="btn btn-sm btn-danger" onclick="TestingView.deleteCycle(${c.id})">🗑</button>
                                    </td>
                                </tr>`).join('')}
                            </tbody>
                        </table>` : '<p style="color:#999;margin-top:8px">No cycles yet.</p>'}
                </div>`;
        }
        container.innerHTML = html;
    }

    function showPlanModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>New Test Plan</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label>
                    <input id="planName" class="form-control" placeholder="e.g. SIT Master Plan"></div>
                <div class="form-group"><label>Description</label>
                    <textarea id="planDesc" class="form-control" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Start Date</label>
                        <input id="planStart" type="date" class="form-control"></div>
                    <div class="form-group"><label>End Date</label>
                        <input id="planEnd" type="date" class="form-control"></div>
                </div>
                <div class="form-group"><label>Entry Criteria</label>
                    <textarea id="planEntry" class="form-control" rows="2"></textarea></div>
                <div class="form-group"><label>Exit Criteria</label>
                    <textarea id="planExit" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestingView.savePlan()">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function savePlan() {
        const body = {
            name: document.getElementById('planName').value,
            description: document.getElementById('planDesc').value,
            start_date: document.getElementById('planStart').value || null,
            end_date: document.getElementById('planEnd').value || null,
            entry_criteria: document.getElementById('planEntry').value,
            exit_criteria: document.getElementById('planExit').value,
        };
        if (!body.name) return App.toast('Name is required', 'error');
        await API.post(`/programs/${selectedProgramId}/testing/plans`, body);
        App.toast('Test plan created', 'success');
        App.closeModal();
        await renderPlans();
    }

    async function deletePlan(id) {
        if (!confirm('Delete this test plan and all its cycles?')) return;
        await API.delete(`/testing/plans/${id}`);
        App.toast('Test plan deleted', 'success');
        await renderPlans();
    }

    function showCycleModal(planId) {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>New Test Cycle</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label>
                    <input id="cycleName" class="form-control" placeholder="e.g. SIT Cycle 1"></div>
                <div class="form-row">
                    <div class="form-group"><label>Test Layer</label>
                        <select id="cycleLayer" class="form-control">
                            ${['sit','uat','unit','regression','performance','cutover_rehearsal'].map(l =>
                                `<option value="${l}">${l.toUpperCase()}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Start Date</label>
                        <input id="cycleStart" type="date" class="form-control"></div>
                    <div class="form-group"><label>End Date</label>
                        <input id="cycleEnd" type="date" class="form-control"></div>
                </div>
                <div class="form-group"><label>Description</label>
                    <textarea id="cycleDesc" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestingView.saveCycle(${planId})">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveCycle(planId) {
        const body = {
            name: document.getElementById('cycleName').value,
            test_layer: document.getElementById('cycleLayer').value,
            start_date: document.getElementById('cycleStart').value || null,
            end_date: document.getElementById('cycleEnd').value || null,
            description: document.getElementById('cycleDesc').value,
        };
        if (!body.name) return App.toast('Name is required', 'error');
        await API.post(`/testing/plans/${planId}/cycles`, body);
        App.toast('Test cycle created', 'success');
        App.closeModal();
        await renderPlans();
    }

    async function deleteCycle(id) {
        if (!confirm('Delete this test cycle?')) return;
        await API.delete(`/testing/cycles/${id}`);
        App.toast('Test cycle deleted', 'success');
        await renderPlans();
    }

    async function viewCycleExecs(cycleId) {
        const data = await API.get(`/testing/cycles/${cycleId}`);
        const execs = data.executions || [];
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');

        const resultBadge = (r) => {
            const c = { pass: '#107e3e', fail: '#c4314b', blocked: '#e9730c', not_run: '#888', deferred: '#6a4fa0' };
            return `<span class="badge" style="background:${c[r] || '#888'};color:#fff">${r}</span>`;
        };

        modal.innerHTML = `
            <div class="modal-header"><h2>${data.name} — Executions</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div style="margin-bottom:12px">
                    <button class="btn btn-primary btn-sm" onclick="TestingView.showExecModal(${cycleId})">+ Add Execution</button>
                </div>
                ${execs.length === 0 ? '<p style="color:#999">No executions yet. Add test case executions to this cycle.</p>' : `
                <table class="data-table">
                    <thead><tr><th>Test Case</th><th>Result</th><th>Tester</th><th>Duration</th><th>Notes</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${execs.map(e => `<tr>
                            <td>TC#${e.test_case_id}</td>
                            <td>${resultBadge(e.result)}</td>
                            <td>${e.executed_by || '-'}</td>
                            <td>${e.duration_minutes ? e.duration_minutes + 'min' : '-'}</td>
                            <td>${e.notes ? e.notes.substring(0, 50) : '-'}</td>
                            <td>
                                <button class="btn btn-sm" onclick="TestingView.showExecEditModal(${e.id}, ${cycleId})">Edit</button>
                                <button class="btn btn-sm btn-danger" onclick="TestingView.deleteExec(${e.id}, ${cycleId})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Close</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    function showExecModal(cycleId) {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>Add Test Execution</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Test Case ID *</label>
                    <input id="execCaseId" class="form-control" type="number" placeholder="Test case ID"></div>
                <div class="form-group"><label>Result</label>
                    <select id="execResult" class="form-control">
                        ${['not_run','pass','fail','blocked','deferred'].map(r =>
                            `<option value="${r}">${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                    </select></div>
                <div class="form-row">
                    <div class="form-group"><label>Executed By</label>
                        <input id="execBy" class="form-control"></div>
                    <div class="form-group"><label>Duration (min)</label>
                        <input id="execDuration" class="form-control" type="number"></div>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="execNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestingView.saveExec(${cycleId})">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveExec(cycleId) {
        const body = {
            test_case_id: parseInt(document.getElementById('execCaseId').value),
            result: document.getElementById('execResult').value,
            executed_by: document.getElementById('execBy').value,
            duration_minutes: parseInt(document.getElementById('execDuration').value) || null,
            notes: document.getElementById('execNotes').value,
        };
        if (!body.test_case_id) return App.toast('Test case ID is required', 'error');
        await API.post(`/testing/cycles/${cycleId}/executions`, body);
        App.toast('Execution added', 'success');
        App.closeModal();
        await viewCycleExecs(cycleId);
    }

    async function showExecEditModal(execId, cycleId) {
        const e = await API.get(`/testing/executions/${execId}`);
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>Edit Execution</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Result</label>
                    <select id="execResult" class="form-control">
                        ${['not_run','pass','fail','blocked','deferred'].map(r =>
                            `<option value="${r}" ${e.result === r ? 'selected' : ''}>${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                    </select></div>
                <div class="form-row">
                    <div class="form-group"><label>Executed By</label>
                        <input id="execBy" class="form-control" value="${e.executed_by || ''}"></div>
                    <div class="form-group"><label>Duration (min)</label>
                        <input id="execDuration" class="form-control" type="number" value="${e.duration_minutes || ''}"></div>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="execNotes" class="form-control" rows="2">${e.notes || ''}</textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestingView.updateExec(${execId}, ${cycleId})">Update</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function updateExec(execId, cycleId) {
        const body = {
            result: document.getElementById('execResult').value,
            executed_by: document.getElementById('execBy').value,
            duration_minutes: parseInt(document.getElementById('execDuration').value) || null,
            notes: document.getElementById('execNotes').value,
        };
        await API.put(`/testing/executions/${execId}`, body);
        App.toast('Execution updated', 'success');
        App.closeModal();
        await viewCycleExecs(cycleId);
    }

    async function deleteExec(execId, cycleId) {
        if (!confirm('Delete this execution?')) return;
        await API.delete(`/testing/executions/${execId}`);
        App.toast('Execution deleted', 'success');
        await viewCycleExecs(cycleId);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // DEFECTS TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderDefects() {
        defects = await API.get(`/programs/${selectedProgramId}/testing/defects`);
        const container = document.getElementById('testContent');

        if (defects.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🐛</div>
                    <div class="empty-state__title">No defects logged</div>
                    <p>No defects have been reported for this program.</p><br>
                    <button class="btn btn-primary" onclick="TestingView.showDefectModal()">+ Report Defect</button>
                </div>`;
            return;
        }

        const sevBadge = (s) => {
            const c = { P1: '#c4314b', P2: '#e9730c', P3: '#e5a800', P4: '#888' };
            return `<span class="badge" style="background:${c[s] || '#888'};color:#fff">${s}</span>`;
        };
        const statusBadge = (s) => {
            const c = { new: '#0070f3', open: '#e9730c', in_progress: '#6a4fa0', fixed: '#107e3e', retest: '#e5a800', closed: '#888', rejected: '#555', reopened: '#c4314b' };
            return `<span class="badge" style="background:${c[s] || '#888'};color:#fff">${s}</span>`;
        };

        container.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                <div style="display:flex;gap:8px">
                    <select id="filterSeverity" class="form-control" style="width:110px" onchange="TestingView.filterDefects()">
                        <option value="">All Sev</option>
                        <option value="P1">P1</option><option value="P2">P2</option>
                        <option value="P3">P3</option><option value="P4">P4</option>
                    </select>
                    <select id="filterDefStatus" class="form-control" style="width:130px" onchange="TestingView.filterDefects()">
                        <option value="">All Status</option>
                        ${['new','open','in_progress','fixed','retest','closed','rejected','reopened'].map(s =>
                            `<option value="${s}">${s}</option>`).join('')}
                    </select>
                    <input id="filterDefSearch" class="form-control" style="width:200px" placeholder="Search..." oninput="TestingView.filterDefects()">
                </div>
                <button class="btn btn-primary" onclick="TestingView.showDefectModal()">+ Report Defect</button>
            </div>
            <table class="data-table">
                <thead><tr>
                    <th>Code</th><th>Title</th><th>Severity</th><th>Status</th>
                    <th>Module</th><th>Aging</th><th>Reopen</th><th>Actions</th>
                </tr></thead>
                <tbody>
                    ${defects.map(d => `<tr>
                        <td><strong>${d.code || '-'}</strong></td>
                        <td>${d.title}</td>
                        <td>${sevBadge(d.severity)}</td>
                        <td>${statusBadge(d.status)}</td>
                        <td>${d.module || '-'}</td>
                        <td>${d.aging_days}d</td>
                        <td>${d.reopen_count || 0}</td>
                        <td>
                            <button class="btn btn-sm" onclick="TestingView.showDefectDetail(${d.id})">Edit</button>
                            <button class="btn btn-sm btn-danger" onclick="TestingView.deleteDefect(${d.id})">🗑</button>
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>
            <div style="margin-top:8px;color:#666;font-size:13px">${defects.length} defect(s)</div>
        `;
    }

    async function filterDefects() {
        const severity = document.getElementById('filterSeverity').value;
        const status = document.getElementById('filterDefStatus').value;
        const search = document.getElementById('filterDefSearch').value;
        let params = [];
        if (severity) params.push(`severity=${severity}`);
        if (status) params.push(`status=${status}`);
        if (search) params.push(`search=${encodeURIComponent(search)}`);
        const qs = params.length ? '?' + params.join('&') : '';
        defects = await API.get(`/programs/${selectedProgramId}/testing/defects${qs}`);
        await renderDefects();
    }

    function showDefectModal(d = null) {
        const isEdit = !!d;
        const title = isEdit ? 'Edit Defect' : 'Report Defect';
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Title *</label>
                    <input id="defTitle" class="form-control" value="${isEdit ? d.title : ''}"></div>
                <div class="form-row">
                    <div class="form-group"><label>Severity</label>
                        <select id="defSeverity" class="form-control">
                            ${['P1','P2','P3','P4'].map(s =>
                                `<option value="${s}" ${(isEdit && d.severity === s) ? 'selected' : ''}>${s}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Status</label>
                        <select id="defStatus" class="form-control">
                            ${['new','open','in_progress','fixed','retest','closed','rejected','reopened'].map(s =>
                                `<option value="${s}" ${(isEdit && d.status === s) ? 'selected' : ''}>${s}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Module</label>
                        <input id="defModule" class="form-control" value="${isEdit ? (d.module || '') : ''}" placeholder="FI, MM, SD..."></div>
                </div>
                <div class="form-group"><label>Description</label>
                    <textarea id="defDesc" class="form-control" rows="2">${isEdit ? (d.description || '') : ''}</textarea></div>
                <div class="form-group"><label>Steps to Reproduce</label>
                    <textarea id="defSteps" class="form-control" rows="3">${isEdit ? (d.steps_to_reproduce || '') : ''}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Reported By</label>
                        <input id="defReporter" class="form-control" value="${isEdit ? (d.reported_by || '') : ''}"></div>
                    <div class="form-group"><label>Assigned To</label>
                        <input id="defAssigned" class="form-control" value="${isEdit ? (d.assigned_to || '') : ''}"></div>
                    <div class="form-group"><label>Environment</label>
                        <input id="defEnv" class="form-control" value="${isEdit ? (d.environment || '') : ''}" placeholder="DEV / QAS / PRD"></div>
                </div>
                <div style="border-top:1px solid #e0e0e0;margin:12px 0 8px;padding-top:8px">
                    <label style="font-weight:600;font-size:13px;color:#666">🔗 Linked Items</label>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Test Case ID</label>
                        <input id="defTestCaseId" class="form-control" type="number" value="${isEdit && d.test_case_id ? d.test_case_id : ''}" placeholder="TC id"></div>
                    <div class="form-group"><label>WRICEF Item ID</label>
                        <input id="defBacklogItemId" class="form-control" type="number" value="${isEdit && d.backlog_item_id ? d.backlog_item_id : ''}" placeholder="Backlog item id"></div>
                    <div class="form-group"><label>Config Item ID</label>
                        <input id="defConfigItemId" class="form-control" type="number" value="${isEdit && d.config_item_id ? d.config_item_id : ''}" placeholder="Config item id"></div>
                </div>
                ${isEdit ? `
                <div class="form-group"><label>Resolution</label>
                    <textarea id="defResolution" class="form-control" rows="2">${d.resolution || ''}</textarea></div>
                <div class="form-group"><label>Root Cause</label>
                    <textarea id="defRootCause" class="form-control" rows="2">${d.root_cause || ''}</textarea></div>
                <div class="form-group"><label>Transport Request</label>
                    <input id="defTransport" class="form-control" value="${d.transport_request || ''}"></div>
                ` : ''}
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestingView.saveDefect(${isEdit ? d.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveDefect(id) {
        const body = {
            title: document.getElementById('defTitle').value,
            severity: document.getElementById('defSeverity').value,
            status: document.getElementById('defStatus').value,
            module: document.getElementById('defModule').value,
            description: document.getElementById('defDesc').value,
            steps_to_reproduce: document.getElementById('defSteps').value,
            reported_by: document.getElementById('defReporter').value,
            assigned_to: document.getElementById('defAssigned').value,
            environment: document.getElementById('defEnv').value,
            test_case_id: parseInt(document.getElementById('defTestCaseId').value) || null,
            backlog_item_id: parseInt(document.getElementById('defBacklogItemId').value) || null,
            config_item_id: parseInt(document.getElementById('defConfigItemId').value) || null,
        };
        if (id) {
            const res = document.getElementById('defResolution');
            if (res) body.resolution = res.value;
            const rc = document.getElementById('defRootCause');
            if (rc) body.root_cause = rc.value;
            const tr = document.getElementById('defTransport');
            if (tr) body.transport_request = tr.value;
        }
        if (!body.title) return App.toast('Title is required', 'error');

        if (id) {
            await API.put(`/testing/defects/${id}`, body);
            App.toast('Defect updated', 'success');
        } else {
            await API.post(`/programs/${selectedProgramId}/testing/defects`, body);
            App.toast('Defect reported', 'success');
        }
        App.closeModal();
        await renderDefects();
    }

    async function showDefectDetail(id) {
        const d = await API.get(`/testing/defects/${id}`);
        showDefectModal(d);
    }

    async function deleteDefect(id) {
        if (!confirm('Delete this defect?')) return;
        await API.delete(`/testing/defects/${id}`);
        App.toast('Defect deleted', 'success');
        await renderDefects();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TRACEABILITY MATRIX TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderTraceability() {
        const data = await API.get(`/programs/${selectedProgramId}/testing/traceability-matrix`);
        const container = document.getElementById('testContent');
        const s = data.summary;

        let html = `
            <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap">
                <div class="kpi-card"><div class="kpi-value">${s.total_requirements}</div><div class="kpi-label">Requirements</div></div>
                <div class="kpi-card"><div class="kpi-value">${s.requirements_with_tests}</div><div class="kpi-label">With Tests</div></div>
                <div class="kpi-card"><div class="kpi-value" style="color:${s.coverage_pct >= 80 ? '#107e3e' : '#c4314b'}">${s.coverage_pct}%</div><div class="kpi-label">Coverage</div></div>
                <div class="kpi-card"><div class="kpi-value">${s.total_test_cases}</div><div class="kpi-label">Test Cases</div></div>
                <div class="kpi-card"><div class="kpi-value">${s.total_defects}</div><div class="kpi-label">Defects</div></div>
            </div>
        `;

        if (data.matrix.length === 0) {
            html += '<div class="empty-state"><p>No requirements found.</p></div>';
        } else {
            html += `
                <table class="data-table">
                    <thead><tr>
                        <th>Requirement</th><th>Priority</th><th>Test Cases</th><th>Defects</th><th>Status</th>
                    </tr></thead>
                    <tbody>
                        ${data.matrix.map(row => {
                            const r = row.requirement;
                            const hasTests = row.total_test_cases > 0;
                            const hasDefects = row.total_defects > 0;
                            return `<tr>
                                <td><strong>${r.code || '-'}</strong> ${r.title}</td>
                                <td>${r.priority || '-'}</td>
                                <td>${hasTests ? `<span style="color:#107e3e">${row.total_test_cases} case(s)</span>` : '<span style="color:#c4314b">—</span>'}</td>
                                <td>${hasDefects ? `<span style="color:#c4314b">${row.total_defects} defect(s)</span>` : '<span style="color:#107e3e">Clean</span>'}</td>
                                <td>${hasTests ? '✅ Covered' : '⚠️ Uncovered'}</td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>`;
        }
        container.innerHTML = html;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // KPI DASHBOARD TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderDashboard() {
        dashboardData = await API.get(`/programs/${selectedProgramId}/testing/dashboard`);
        const d = dashboardData;
        const container = document.getElementById('testContent');

        container.innerHTML = `
            <div style="display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap">
                <div class="kpi-card"><div class="kpi-value" style="color:${d.pass_rate >= 80 ? '#107e3e' : '#c4314b'}">${d.pass_rate}%</div><div class="kpi-label">Pass Rate</div></div>
                <div class="kpi-card"><div class="kpi-value">${d.total_test_cases}</div><div class="kpi-label">Test Cases</div></div>
                <div class="kpi-card"><div class="kpi-value">${d.total_executed}</div><div class="kpi-label">Executed</div></div>
                <div class="kpi-card"><div class="kpi-value">${d.total_defects}</div><div class="kpi-label">Total Defects</div></div>
                <div class="kpi-card"><div class="kpi-value" style="color:${d.open_defects > 0 ? '#c4314b' : '#107e3e'}">${d.open_defects}</div><div class="kpi-label">Open Defects</div></div>
                <div class="kpi-card"><div class="kpi-value">${d.reopen_rate}%</div><div class="kpi-label">Reopen Rate</div></div>
                <div class="kpi-card"><div class="kpi-value" style="color:${d.coverage.coverage_pct >= 80 ? '#107e3e' : '#c4314b'}">${d.coverage.coverage_pct}%</div><div class="kpi-label">Req Coverage</div></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
                <div class="card" style="padding:16px"><h3>Severity Distribution</h3><canvas id="chartSeverity"></canvas></div>
                <div class="card" style="padding:16px"><h3>Defect Velocity (12 Weeks)</h3><canvas id="chartVelocity"></canvas></div>
                <div class="card" style="padding:16px"><h3>Test Layer Summary</h3><canvas id="chartLayers"></canvas></div>
                <div class="card" style="padding:16px"><h3>Cycle Burndown</h3><canvas id="chartBurndown"></canvas></div>
                <div class="card" style="padding:16px">
                    <h3>Top Open Defects by Aging</h3>
                    ${d.defect_aging.length === 0 ? '<p style="color:#999">No open defects</p>' : `
                    <table class="data-table">
                        <thead><tr><th>Code</th><th>Title</th><th>Severity</th><th>Aging</th></tr></thead>
                        <tbody>
                            ${d.defect_aging.slice(0, 10).map(da => `<tr>
                                <td><strong>${da.code || '-'}</strong></td>
                                <td>${da.title}</td>
                                <td>${da.severity}</td>
                                <td style="color:${da.aging_days > 7 ? '#c4314b' : '#888'}">${da.aging_days}d</td>
                            </tr>`).join('')}
                        </tbody>
                    </table>`}
                </div>
            </div>
        `;

        // Render charts
        renderSeverityChart(d.severity_distribution);
        renderVelocityChart(d.defect_velocity || []);
        renderLayerChart(d.test_layer_summary);
        renderBurndownChart(d.cycle_burndown);
    }

    function renderVelocityChart(velocity) {
        const ctx = document.getElementById('chartVelocity');
        if (!ctx || !velocity.length) return;
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: velocity.map(v => v.week),
                datasets: [{
                    label: 'Defects Reported',
                    data: velocity.map(v => v.count),
                    borderColor: '#c4314b',
                    backgroundColor: 'rgba(196,49,75,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointBackgroundColor: '#c4314b',
                }],
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
                plugins: { legend: { position: 'bottom' } },
            },
        });
    }

    function renderSeverityChart(dist) {
        const ctx = document.getElementById('chartSeverity');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['P1 (Blocker)', 'P2 (Critical)', 'P3 (Major)', 'P4 (Minor)'],
                datasets: [{
                    data: [dist.P1, dist.P2, dist.P3, dist.P4],
                    backgroundColor: ['#c4314b', '#e9730c', '#e5a800', '#888'],
                }],
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
        });
    }

    function renderLayerChart(layers) {
        const labels = Object.keys(layers).map(l => l.toUpperCase());
        const totals = Object.values(layers).map(v => v.total);
        const passed = Object.values(layers).map(v => v.passed);
        const failed = Object.values(layers).map(v => v.failed);

        const ctx = document.getElementById('chartLayers');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Total', data: totals, backgroundColor: '#0070f3' },
                    { label: 'Passed', data: passed, backgroundColor: '#107e3e' },
                    { label: 'Failed', data: failed, backgroundColor: '#c4314b' },
                ],
            },
            options: { responsive: true, scales: { y: { beginAtZero: true } }, plugins: { legend: { position: 'bottom' } } },
        });
    }

    function renderBurndownChart(burndown) {
        if (!burndown.length) return;
        const ctx = document.getElementById('chartBurndown');
        if (!ctx) return;
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: burndown.map(c => c.cycle_name),
                datasets: [
                    { label: 'Completed', data: burndown.map(c => c.completed), backgroundColor: '#107e3e' },
                    { label: 'Remaining', data: burndown.map(c => c.remaining), backgroundColor: '#e9730c' },
                ],
            },
            options: { responsive: true, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }, plugins: { legend: { position: 'bottom' } } },
        });
    }

    // ── Public API ─────────────────────────────────────────────────────────
    return {
        render,
        onProgramChange,
        switchTab,
        // Catalog
        showCaseModal,
        saveCase,
        showCaseDetail,
        deleteCase,
        filterCatalog,
        // Plans & Cycles
        showPlanModal,
        savePlan,
        deletePlan,
        showCycleModal,
        saveCycle,
        deleteCycle,
        viewCycleExecs,
        showExecModal,
        saveExec,
        showExecEditModal,
        updateExec,
        deleteExec,
        // Defects
        showDefectModal,
        saveDefect,
        showDefectDetail,
        deleteDefect,
        filterDefects,
    };
})();
