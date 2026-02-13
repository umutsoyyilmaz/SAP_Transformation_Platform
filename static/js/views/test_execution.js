/**
 * SAP Transformation Management Platform
 * Test Execution View — Plans & Cycles, Test Runs, Traceability
 * Extracted from testing.js (Sprint refactor)
 */

const TestExecutionView = (() => {
    const esc = TestingShared.esc;
    let currentTab = 'plans';

    // State
    let testPlans = [];

    // ── Main render ───────────────────────────────────────────────────
    async function render() {
        const pid = TestingShared.getProgram();
        const main = document.getElementById('mainContent');

        if (!pid) {
            main.innerHTML = TestingShared.noProgramHtml('Test Execution');
            return;
        }

        main.innerHTML = `
            <div class="page-header"><h1>▶️ Test Execution</h1></div>
            <div class="tabs" id="testExecTabs">
                <div class="tab active" data-tab="plans" onclick="TestExecutionView.switchTab('plans')">📅 Plans & Cycles</div>
                <div class="tab" data-tab="traceability" onclick="TestExecutionView.switchTab('traceability')">🔗 Traceability</div>
            </div>
            <div class="card" id="testContent">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>
        `;
        await loadTabData();
    }

    function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('#testExecTabs .tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        if (TestingShared.pid) loadTabData();
    }

    async function loadTabData() {
        const container = document.getElementById('testContent');
        container.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';
        try {
            switch (currentTab) {
                case 'plans': await renderPlans(); break;
                case 'traceability': await renderTraceability(); break;
            }
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PLANS & CYCLES TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderPlans() {
        const pid = TestingShared.pid;
        const _pres = await API.get(`/programs/${pid}/testing/plans`);
        testPlans = _pres.items || _pres || [];
        const container = document.getElementById('testContent');

        if (testPlans.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📅</div>
                    <div class="empty-state__title">No test plans yet</div>
                    <p>Create a test plan to organize test cycles.</p><br>
                    <button class="btn btn-primary" onclick="TestExecutionView.showPlanModal()">+ New Test Plan</button>
                </div>`;
            return;
        }

        let html = `
            <div style="display:flex;justify-content:space-between;margin-bottom:16px">
                <h3 style="margin:0">Test Plans</h3>
                <button class="btn btn-primary" onclick="TestExecutionView.showPlanModal()">+ New Test Plan</button>
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
                            <button class="btn btn-sm" onclick="TestExecutionView.showCycleModal(${plan.id})">+ Cycle</button>
                            <button class="btn btn-sm btn-danger" onclick="TestExecutionView.deletePlan(${plan.id})">🗑</button>
                        </div>
                    </div>
                    ${plan.description ? `<p style="color:#666;margin:4px 0">${plan.description}</p>` : ''}
                    ${detail.cycles && detail.cycles.length > 0 ? `
                        <table class="data-table" style="margin-top:10px">
                            <thead><tr><th>Cycle</th><th>Layer</th><th>Status</th><th>Start</th><th>End</th><th>Actions</th></tr></thead>
                            <tbody>
                                ${detail.cycles.map(c => `<tr onclick="TestExecutionView.viewCycleExecs(${c.id})" style="cursor:pointer" class="clickable-row">
                                    <td><strong>${c.name}</strong></td>
                                    <td>${(c.test_layer || '-').toUpperCase()}</td>
                                    <td><span class="badge">${c.status}</span></td>
                                    <td>${c.start_date || '-'}</td>
                                    <td>${c.end_date || '-'}</td>
                                    <td>
                                        <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();TestExecutionView.deleteCycle(${c.id})">🗑</button>
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
                <button class="btn btn-primary" onclick="TestExecutionView.savePlan()">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function savePlan() {
        const pid = TestingShared.pid;
        const body = {
            name: document.getElementById('planName').value,
            description: document.getElementById('planDesc').value,
            start_date: document.getElementById('planStart').value || null,
            end_date: document.getElementById('planEnd').value || null,
            entry_criteria: document.getElementById('planEntry').value,
            exit_criteria: document.getElementById('planExit').value,
        };
        if (!body.name) return App.toast('Name is required', 'error');
        await API.post(`/programs/${pid}/testing/plans`, body);
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
                <button class="btn btn-primary" onclick="TestExecutionView.saveCycle(${planId})">Create</button>
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
                <div style="margin-bottom:12px;display:flex;gap:8px">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.showExecModal(${cycleId})">+ Add Execution</button>
                    <button class="btn btn-sm" style="background:#0070f3;color:#fff" onclick="TestExecutionView.viewCycleRuns(${cycleId})">▶ Test Runs</button>
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
                                <button class="btn btn-sm" onclick="TestExecutionView.showExecEditModal(${e.id}, ${cycleId})">Edit</button>
                                <button class="btn btn-sm btn-danger" onclick="TestExecutionView.deleteExec(${e.id}, ${cycleId})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}

                <!-- Entry/Exit Criteria -->
                <div style="border-top:2px solid #e0e0e0;margin-top:16px;padding-top:12px">
                    <h3 style="margin-bottom:8px">📋 Entry / Exit Criteria</h3>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                        <div>
                            <h4 style="margin-bottom:4px">Entry Criteria</h4>
                            <div id="entryCriteriaList_${cycleId}">
                                ${(data.entry_criteria && data.entry_criteria.length > 0)
                                    ? data.entry_criteria.map((c, i) => `
                                        <div style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid #f0f0f0">
                                            <span style="font-size:14px">${c.met ? '✅' : '❌'}</span>
                                            <span style="color:${c.met ? '#107e3e' : '#c4314b'}">${esc(c.criterion || 'Unknown')}</span>
                                        </div>`).join('')
                                    : '<p style="color:#999;font-size:13px">No entry criteria defined for this cycle.</p>'}
                            </div>
                            <button class="btn btn-sm" style="margin-top:8px" onclick="TestExecutionView.validateEntry(${cycleId}, false)">✓ Validate Entry</button>
                            <button class="btn btn-sm" style="margin-top:8px;margin-left:4px" onclick="TestExecutionView.validateEntry(${cycleId}, true)" title="Force override">⚡ Force</button>
                        </div>
                        <div>
                            <h4 style="margin-bottom:4px">Exit Criteria</h4>
                            <div id="exitCriteriaList_${cycleId}">
                                ${(data.exit_criteria && data.exit_criteria.length > 0)
                                    ? data.exit_criteria.map((c, i) => `
                                        <div style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid #f0f0f0">
                                            <span style="font-size:14px">${c.met ? '✅' : '❌'}</span>
                                            <span style="color:${c.met ? '#107e3e' : '#c4314b'}">${esc(c.criterion || 'Unknown')}</span>
                                        </div>`).join('')
                                    : '<p style="color:#999;font-size:13px">No exit criteria defined for this cycle.</p>'}
                            </div>
                            <button class="btn btn-sm" style="margin-top:8px" onclick="TestExecutionView.validateExit(${cycleId}, false)">✓ Validate Exit</button>
                            <button class="btn btn-sm" style="margin-top:8px;margin-left:4px" onclick="TestExecutionView.validateExit(${cycleId}, true)" title="Force override">⚡ Force</button>
                        </div>
                    </div>
                </div>

                <!-- UAT Sign-off -->
                <div style="border-top:2px solid #e0e0e0;margin-top:16px;padding-top:12px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                        <h3 style="margin:0">🔏 UAT Sign-off</h3>
                        <button class="btn btn-sm btn-primary" onclick="TestExecutionView.showSignoffModal(${cycleId})">+ Initiate Sign-off</button>
                    </div>
                    <div id="uatSignoffList_${cycleId}"><div class="spinner" style="margin:8px auto"></div></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Close</button>
            </div>
        `;
        overlay.classList.add('open');
        _loadUatSignoffs(cycleId);
    }

    async function showExecModal(cycleId) {
        const pid = TestingShared.pid;
        const members = await TeamMemberPicker.fetchMembers(pid);
        const execByHtml = TeamMemberPicker.renderSelect('execBy', members, '', { cssClass: 'form-control', placeholder: '— Select Tester —' });
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
                        ${execByHtml}</div>
                    <div class="form-group"><label>Duration (min)</label>
                        <input id="execDuration" class="form-control" type="number"></div>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="execNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.saveExec(${cycleId})">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveExec(cycleId) {
        const body = {
            test_case_id: parseInt(document.getElementById('execCaseId').value),
            result: document.getElementById('execResult').value,
            executed_by: document.getElementById('execBy').value,
            executed_by_id: document.getElementById('execBy').value ? parseInt(document.getElementById('execBy').value) : null,
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
        const pid = TestingShared.pid;
        const members = await TeamMemberPicker.fetchMembers(pid);
        const execByHtml = TeamMemberPicker.renderSelect('execBy', members, e.executed_by_id || e.executed_by || '', { cssClass: 'form-control', placeholder: '— Select Tester —' });
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
                        ${execByHtml}</div>
                    <div class="form-group"><label>Duration (min)</label>
                        <input id="execDuration" class="form-control" type="number" value="${e.duration_minutes || ''}"></div>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="execNotes" class="form-control" rows="2">${e.notes || ''}</textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.updateExec(${execId}, ${cycleId})">Update</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function updateExec(execId, cycleId) {
        const body = {
            result: document.getElementById('execResult').value,
            executed_by: document.getElementById('execBy').value,
            executed_by_id: document.getElementById('execBy').value ? parseInt(document.getElementById('execBy').value) : null,
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

    // ── UAT Sign-off ─────────────────────────────────────────────────────
    async function _loadUatSignoffs(cycleId) {
        try {
            const signoffs = await API.get(`/testing/uat-signoffs?cycle_id=${cycleId}`);
            const el = document.getElementById(`uatSignoffList_${cycleId}`);
            if (!el) return;
            if (signoffs.length === 0) {
                el.innerHTML = '<p style="color:#999;font-size:13px">No sign-offs initiated yet.</p>';
                return;
            }
            const statusColor = { pending: '#e5a800', approved: '#107e3e', rejected: '#c4314b' };
            const statusIcon = { pending: '⏳', approved: '✅', rejected: '❌' };
            el.innerHTML = `
                <table class="data-table">
                    <thead><tr><th>Process Area</th><th>Signed By</th><th>Role</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${signoffs.map(s => `<tr>
                            <td>${esc(s.process_area)}</td>
                            <td>${esc(s.signed_off_by || '-')}</td>
                            <td>${esc(s.role || '-')}</td>
                            <td><span class="badge" style="background:${statusColor[s.status] || '#888'};color:#fff">${statusIcon[s.status] || ''} ${s.status}</span></td>
                            <td>${s.sign_off_date ? new Date(s.sign_off_date).toLocaleDateString() : '-'}</td>
                            <td>
                                ${s.status === 'pending' ? `
                                    <button class="btn btn-sm" style="background:#107e3e;color:#fff" onclick="TestExecutionView.updateSignoff(${s.id}, 'approved', ${cycleId})">Approve</button>
                                    <button class="btn btn-sm btn-danger" onclick="TestExecutionView.updateSignoff(${s.id}, 'rejected', ${cycleId})">Reject</button>
                                ` : ''}
                                <button class="btn btn-sm btn-danger" onclick="TestExecutionView.deleteSignoff(${s.id}, ${cycleId})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`;
        } catch(e) {
            const el = document.getElementById(`uatSignoffList_${cycleId}`);
            if (el) el.innerHTML = `<p style="color:#c4314b">Error: ${esc(e.message)}</p>`;
        }
    }

    function showSignoffModal(cycleId) {
        App.closeModal();
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>🔏 New UAT Sign-off</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Process Area *</label>
                    <input id="signoffArea" class="form-control" placeholder="e.g. FI, MM, SD"></div>
                <div class="form-row">
                    <div class="form-group"><label>Signed Off By *</label>
                        <input id="signoffBy" class="form-control" placeholder="Name"></div>
                    <div class="form-group"><label>Role *</label>
                        <select id="signoffRole" class="form-control">
                            <option value="BPO">BPO</option><option value="PM">PM</option>
                        </select></div>
                </div>
                <div class="form-group"><label>Comments</label>
                    <textarea id="signoffComments" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="TestExecutionView.viewCycleExecs(${cycleId})">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.createSignoff(${cycleId})">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function createSignoff(cycleId) {
        const body = {
            process_area: document.getElementById('signoffArea').value,
            signed_off_by: document.getElementById('signoffBy').value,
            role: document.getElementById('signoffRole').value,
            comments: document.getElementById('signoffComments').value,
        };
        if (!body.process_area || !body.signed_off_by) return App.toast('Process area and signer are required', 'error');
        try {
            await API.post(`/testing/cycles/${cycleId}/uat-signoffs`, body);
            App.toast('Sign-off initiated', 'success');
            App.closeModal();
            await viewCycleExecs(cycleId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    async function updateSignoff(signoffId, status, cycleId) {
        try {
            await API.put(`/testing/uat-signoffs/${signoffId}`, { status });
            App.toast(`Sign-off ${status}`, 'success');
            await _loadUatSignoffs(cycleId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    async function deleteSignoff(signoffId, cycleId) {
        if (!confirm('Delete this sign-off?')) return;
        try {
            await API.delete(`/testing/uat-signoffs/${signoffId}`);
            App.toast('Sign-off deleted', 'success');
            await _loadUatSignoffs(cycleId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    // ── Entry/Exit Criteria Validation ────────────────────────────────────
    async function validateEntry(cycleId, force) {
        try {
            const result = await API.post(`/testing/cycles/${cycleId}/validate-entry`, { force });
            if (result.valid) {
                App.toast(result.message || 'Entry criteria met — cycle started!', 'success');
                await viewCycleExecs(cycleId);
            } else {
                const unmet = result.unmet_criteria || [];
                App.toast(`Entry blocked: ${unmet.join(', ')}`, 'error');
            }
        } catch(e) {
            App.toast('Validation failed: ' + e.message, 'error');
        }
    }

    async function validateExit(cycleId, force) {
        try {
            const result = await API.post(`/testing/cycles/${cycleId}/validate-exit`, { force });
            if (result.valid) {
                App.toast(result.message || 'Exit criteria met — cycle completed!', 'success');
                await viewCycleExecs(cycleId);
            } else {
                const unmet = result.unmet_criteria || [];
                App.toast(`Exit blocked: ${unmet.join(', ')}`, 'error');
            }
        } catch(e) {
            App.toast('Validation failed: ' + e.message, 'error');
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TEST RUNS
    // ═══════════════════════════════════════════════════════════════════════
    async function viewCycleRuns(cycleId) {
        const _rres = await API.get(`/testing/cycles/${cycleId}/runs`);
        const runs = _rres.items || _rres || [];
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');

        const statusBadge = (s) => {
            const c = {not_started:'#888',in_progress:'#0070f3',completed:'#107e3e',aborted:'#c4314b'};
            return `<span class="badge" style="background:${c[s]||'#888'};color:#fff">${s.replace('_',' ')}</span>`;
        };
        const resultBadge = (r) => {
            const c = {pass:'#107e3e',fail:'#c4314b',blocked:'#e9730c',not_run:'#888',deferred:'#6a4fa0'};
            return `<span class="badge" style="background:${c[r]||'#888'};color:#fff">${r}</span>`;
        };

        modal.innerHTML = `
            <div class="modal-header"><h2>Test Runs — Cycle #${cycleId}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div style="margin-bottom:12px;display:flex;gap:8px">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.showNewRunModal(${cycleId})">+ New Run</button>
                    <button class="btn btn-sm" onclick="TestExecutionView.viewCycleExecs(${cycleId})">← Back to Executions</button>
                </div>
                ${runs.length === 0 ? '<p style="color:#999">No test runs yet. Start a new run to begin step-by-step execution.</p>' : `
                <table class="data-table">
                    <thead><tr><th>Run</th><th>Test Case</th><th>Type</th><th>Status</th><th>Result</th><th>Tester</th><th>Environment</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${runs.map(r => `<tr>
                            <td>#${r.id}</td>
                            <td>TC#${r.test_case_id}</td>
                            <td>${r.run_type || 'manual'}</td>
                            <td>${statusBadge(r.status)}</td>
                            <td>${resultBadge(r.result)}</td>
                            <td>${r.tester || '-'}</td>
                            <td>${r.environment || '-'}</td>
                            <td>
                                <button class="btn btn-sm btn-primary" onclick="TestExecutionView.openRunExecution(${r.id}, ${cycleId})">▶ Execute</button>
                                <button class="btn btn-sm btn-danger" onclick="TestExecutionView.deleteRun(${r.id}, ${cycleId})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Close</button>
            </div>`;
        overlay.classList.add('open');
    }

    function showNewRunModal(cycleId) {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>New Test Run</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body">
                <div class="form-group"><label>Test Case ID *</label>
                    <input id="runCaseId" class="form-control" type="number" placeholder="Test case ID"></div>
                <div class="form-row">
                    <div class="form-group"><label>Run Type</label>
                        <select id="runType" class="form-control">
                            ${['manual','automated','exploratory'].map(t =>
                                `<option value="${t}">${t.charAt(0).toUpperCase()+t.slice(1)}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Tester</label>
                        <input id="runTester" class="form-control" placeholder="Tester name"></div>
                    <div class="form-group"><label>Environment</label>
                        <input id="runEnv" class="form-control" placeholder="DEV / QAS / PRD"></div>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="runNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="TestExecutionView.viewCycleRuns(${cycleId})">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.saveNewRun(${cycleId})">Create & Open</button>
            </div>`;
        overlay.classList.add('open');
    }

    async function saveNewRun(cycleId) {
        const body = {
            test_case_id: parseInt(document.getElementById('runCaseId').value),
            run_type: document.getElementById('runType').value,
            tester: document.getElementById('runTester').value || null,
            environment: document.getElementById('runEnv').value || null,
            notes: document.getElementById('runNotes').value || null,
        };
        if (!body.test_case_id) return App.toast('Test Case ID is required', 'error');
        const run = await API.post(`/testing/cycles/${cycleId}/runs`, body);
        App.toast('Run created', 'success');
        await openRunExecution(run.id, cycleId);
    }

    async function openRunExecution(runId, cycleId) {
        const run = await API.get(`/testing/runs/${runId}`);
        const stepResults = await API.get(`/testing/runs/${runId}/step-results`);
        let steps = [];
        try {
            const tc = await API.get(`/testing/test-cases/${run.test_case_id}`);
            steps = tc.steps || [];
        } catch(e) { /* test case may not have steps */ }

        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');

        const statusBadge = (s) => {
            const c = {not_started:'#888',in_progress:'#0070f3',completed:'#107e3e',aborted:'#c4314b'};
            return `<span class="badge" style="background:${c[s]||'#888'};color:#fff">${s.replace('_',' ')}</span>`;
        };
        const resultBadge = (r) => {
            const c = {pass:'#107e3e',fail:'#c4314b',blocked:'#e9730c',not_run:'#888',skipped:'#6a4fa0'};
            return `<span class="badge" style="background:${c[r]||'#888'};color:#fff">${r}</span>`;
        };

        const resultMap = {};
        stepResults.forEach(sr => { resultMap[sr.step_no] = sr; });

        let stepRowsHtml = '';
        const stepList = steps.length > 0 ? steps : [];

        if (stepList.length > 0) {
            stepRowsHtml = stepList.map((s, idx) => {
                const no = idx + 1;
                const sr = resultMap[no];
                const currentResult = sr ? sr.result : 'not_run';
                const actualResult = sr ? (sr.actual_result || '') : '';
                const notes = sr ? (sr.notes || '') : '';
                return `<tr data-step-no="${no}" data-step-id="${s.id || ''}" data-sr-id="${sr ? sr.id : ''}">
                    <td><strong>${no}</strong></td>
                    <td>${esc(s.action || s.description || '-')}</td>
                    <td>${esc(s.expected_result || '-')}</td>
                    <td>
                        <select class="form-control run-step-result" style="width:100px" data-step-no="${no}">
                            ${['not_run','pass','fail','blocked','skipped'].map(r =>
                                `<option value="${r}" ${r===currentResult?'selected':''}>${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                        </select>
                    </td>
                    <td><input class="form-control run-step-actual" style="width:100%" value="${esc(actualResult)}" data-step-no="${no}" placeholder="Actual result..."></td>
                    <td><input class="form-control run-step-notes" style="width:100%" value="${esc(notes)}" data-step-no="${no}" placeholder="Notes..."></td>
                </tr>`;
            }).join('');
        } else {
            if (stepResults.length > 0) {
                stepRowsHtml = stepResults.map(sr => `<tr data-step-no="${sr.step_no}" data-sr-id="${sr.id}">
                    <td><strong>${sr.step_no}</strong></td>
                    <td>—</td><td>—</td>
                    <td>
                        <select class="form-control run-step-result" style="width:100px" data-step-no="${sr.step_no}">
                            ${['not_run','pass','fail','blocked','skipped'].map(r =>
                                `<option value="${r}" ${r===sr.result?'selected':''}>${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                        </select>
                    </td>
                    <td><input class="form-control run-step-actual" style="width:100%" value="${esc(sr.actual_result||'')}" data-step-no="${sr.step_no}"></td>
                    <td><input class="form-control run-step-notes" style="width:100%" value="${esc(sr.notes||'')}" data-step-no="${sr.step_no}"></td>
                </tr>`).join('');
            } else {
                stepRowsHtml = `<tr data-step-no="1" data-sr-id="">
                    <td><strong>1</strong></td><td>—</td><td>—</td>
                    <td><select class="form-control run-step-result" data-step-no="1">
                        ${['not_run','pass','fail','blocked','skipped'].map(r => `<option value="${r}">${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                    </select></td>
                    <td><input class="form-control run-step-actual" data-step-no="1" placeholder="Actual result..."></td>
                    <td><input class="form-control run-step-notes" data-step-no="1" placeholder="Notes..."></td>
                </tr>`;
            }
        }

        modal.innerHTML = `
            <div class="modal-header">
                <h2>▶ Run #${run.id} — TC#${run.test_case_id} ${statusBadge(run.status)} ${resultBadge(run.result)}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <div class="modal-body" style="max-height:70vh;overflow-y:auto">
                <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center">
                    <span><strong>Type:</strong> ${run.run_type || 'manual'}</span>
                    <span><strong>Tester:</strong> ${run.tester || '-'}</span>
                    <span><strong>Environment:</strong> ${run.environment || '-'}</span>
                    ${run.started_at ? `<span><strong>Started:</strong> ${new Date(run.started_at).toLocaleString()}</span>` : ''}
                    ${run.finished_at ? `<span><strong>Finished:</strong> ${new Date(run.finished_at).toLocaleString()}</span>` : ''}
                </div>

                <div style="display:flex;gap:8px;margin-bottom:16px">
                    ${run.status === 'not_started' ? `<button class="btn btn-primary btn-sm" onclick="TestExecutionView.updateRunStatus(${run.id}, ${cycleId}, 'in_progress')">▶ Start Run</button>` : ''}
                    ${run.status === 'in_progress' ? `
                        <button class="btn btn-sm" style="background:#107e3e;color:#fff" onclick="TestExecutionView.completeRun(${run.id}, ${cycleId}, 'pass')">✅ Complete (Pass)</button>
                        <button class="btn btn-sm" style="background:#c4314b;color:#fff" onclick="TestExecutionView.completeRun(${run.id}, ${cycleId}, 'fail')">❌ Complete (Fail)</button>
                        <button class="btn btn-sm" onclick="TestExecutionView.updateRunStatus(${run.id}, ${cycleId}, 'aborted')">⛔ Abort</button>
                    ` : ''}
                    ${run.status === 'completed' || run.status === 'aborted' ? `<span style="color:#666;font-style:italic">Run is ${run.status}</span>` : ''}
                </div>

                <h3 style="margin-bottom:8px">Step Results</h3>
                <table class="data-table" id="runStepsTable">
                    <thead><tr><th>#</th><th>Action</th><th>Expected</th><th>Result</th><th>Actual Result</th><th>Notes</th></tr></thead>
                    <tbody>${stepRowsHtml}</tbody>
                </table>
                <div style="margin-top:12px;display:flex;gap:8px">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.saveStepResults(${run.id}, ${cycleId})">💾 Save Step Results</button>
                    <button class="btn btn-sm" onclick="TestExecutionView.addStepResultRow()">+ Add Step Row</button>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="TestExecutionView.viewCycleRuns(${cycleId})">← Back to Runs</button>
                <button class="btn" onclick="App.closeModal()">Close</button>
            </div>`;
        overlay.classList.add('open');
    }

    function addStepResultRow() {
        const tbody = document.querySelector('#runStepsTable tbody');
        if (!tbody) return;
        const rows = tbody.querySelectorAll('tr');
        const nextNo = rows.length + 1;
        const tr = document.createElement('tr');
        tr.setAttribute('data-step-no', nextNo);
        tr.setAttribute('data-sr-id', '');
        tr.innerHTML = `
            <td><strong>${nextNo}</strong></td><td>—</td><td>—</td>
            <td><select class="form-control run-step-result" data-step-no="${nextNo}">
                ${['not_run','pass','fail','blocked','skipped'].map(r => `<option value="${r}">${r.replace('_',' ').toUpperCase()}</option>`).join('')}
            </select></td>
            <td><input class="form-control run-step-actual" data-step-no="${nextNo}" placeholder="Actual result..."></td>
            <td><input class="form-control run-step-notes" data-step-no="${nextNo}" placeholder="Notes..."></td>`;
        tbody.appendChild(tr);
    }

    async function saveStepResults(runId, cycleId) {
        const rows = document.querySelectorAll('#runStepsTable tbody tr');
        for (const row of rows) {
            const stepNo = parseInt(row.dataset.stepNo);
            const srId = row.dataset.srId;
            const stepId = row.dataset.stepId || null;
            const result = row.querySelector('.run-step-result')?.value || 'not_run';
            const actualResult = row.querySelector('.run-step-actual')?.value || '';
            const notes = row.querySelector('.run-step-notes')?.value || '';

            const body = {
                step_no: stepNo,
                result: result,
                actual_result: actualResult,
                notes: notes,
            };
            if (stepId) body.step_id = stepId;

            if (srId) {
                await API.put(`/testing/step-results/${srId}`, body);
            } else {
                const created = await API.post(`/testing/runs/${runId}/step-results`, body);
                row.dataset.srId = created.id;
            }
        }
        App.toast('Step results saved', 'success');
        await openRunExecution(runId, cycleId);
    }

    async function updateRunStatus(runId, cycleId, status) {
        await API.put(`/testing/runs/${runId}`, { status });
        App.toast(`Run status → ${status}`, 'success');
        await openRunExecution(runId, cycleId);
    }

    async function completeRun(runId, cycleId, result) {
        await API.put(`/testing/runs/${runId}`, { status: 'completed', result });
        App.toast(`Run completed — ${result}`, 'success');
        await openRunExecution(runId, cycleId);
    }

    async function deleteRun(runId, cycleId) {
        if (!confirm('Delete this test run?')) return;
        await API.delete(`/testing/runs/${runId}`);
        App.toast('Run deleted', 'success');
        await viewCycleRuns(cycleId);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TRACEABILITY MATRIX TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderTraceability() {
        const pid = TestingShared.pid;
        const data = await API.get(`/programs/${pid}/testing/traceability-matrix`);
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

    // ── Go/No-Go Scorecard ───────────────────────────────────────────────
    async function loadGoNoGo() {
        const pid = TestingShared.pid;
        try {
            const data = await API.get(`/programs/${pid}/testing/dashboard/go-no-go`);
            const el = document.getElementById('goNoGoContent');
            if (!el) return;
            const overallColor = data.overall === 'go' ? '#107e3e' : '#c4314b';
            const overallText = data.overall === 'go' ? '✅ GO' : '🛑 NO-GO';

            el.innerHTML = `
                <div style="text-align:center;padding:12px;margin-bottom:16px;background:${overallColor}10;border:2px solid ${overallColor};border-radius:8px">
                    <div style="font-size:28px;font-weight:bold;color:${overallColor}">${overallText}</div>
                    <div style="color:#666;margin-top:4px">${data.green_count} green · ${data.yellow_count} yellow · ${data.red_count} red</div>
                </div>
                <table class="data-table">
                    <thead><tr><th>Criterion</th><th>Target</th><th>Actual</th><th>Status</th></tr></thead>
                    <tbody>
                        ${data.scorecard.map(s => {
                            const sc = { green: '#107e3e', yellow: '#e5a800', red: '#c4314b' };
                            const si = { green: '✅', yellow: '⚠️', red: '❌' };
                            return `<tr style="border-left:4px solid ${sc[s.status]}">
                                <td><strong>${esc(s.criterion)}</strong></td>
                                <td>${esc(s.target)}</td>
                                <td><strong>${typeof s.actual === 'number' ? (s.actual % 1 === 0 ? s.actual : s.actual + '%') : s.actual}</strong></td>
                                <td>${si[s.status]} <span class="badge" style="background:${sc[s.status]};color:#fff">${s.status.toUpperCase()}</span></td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>`;
        } catch(e) {
            const el = document.getElementById('goNoGoContent');
            if (el) el.innerHTML = `<p style="color:#c4314b">Error loading scorecard: ${esc(e.message)}</p>`;
        }
    }

    // ── Daily Snapshots ──────────────────────────────────────────────────
    async function loadSnapshots() {
        const pid = TestingShared.pid;
        try {
            const snapshots = await API.get(`/programs/${pid}/testing/snapshots`);
            const el = document.getElementById('snapshotsContent');
            if (!el) return;
            if (snapshots.length === 0) {
                el.innerHTML = '<p style="color:#999;text-align:center">No snapshots yet. Click "Capture Snapshot" to take the first one.</p>';
                return;
            }
            el.innerHTML = `
                <table class="data-table">
                    <thead><tr><th>Date</th><th>Total</th><th>Passed</th><th>Failed</th><th>Blocked</th><th>Pass Rate</th><th>Open Defects</th></tr></thead>
                    <tbody>
                        ${snapshots.slice(0, 14).map(s => {
                            const total = s.passed + s.failed + s.blocked + s.not_run;
                            const pr = total > 0 ? Math.round(s.passed / total * 100) : 0;
                            const openDef = (s.open_defects_s1 || 0) + (s.open_defects_s2 || 0) + (s.open_defects_s3 || 0) + (s.open_defects_s4 || 0);
                            return `<tr>
                                <td>${s.snapshot_date}</td>
                                <td>${s.total_cases}</td>
                                <td style="color:#107e3e">${s.passed}</td>
                                <td style="color:#c4314b">${s.failed}</td>
                                <td style="color:#e9730c">${s.blocked}</td>
                                <td><strong style="color:${pr >= 80 ? '#107e3e' : '#c4314b'}">${pr}%</strong></td>
                                <td>${openDef}</td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>`;

            _renderSnapshotChart(snapshots.slice(0, 30).reverse());
        } catch(e) {
            const el = document.getElementById('snapshotsContent');
            if (el) el.innerHTML = `<p style="color:#c4314b">Error loading snapshots: ${esc(e.message)}</p>`;
        }
    }

    function _renderSnapshotChart(snapshots) {
        const ctx = document.getElementById('chartSnapshots');
        if (!ctx || !snapshots.length) return;
        const labels = snapshots.map(s => s.snapshot_date);
        const passRates = snapshots.map(s => {
            const total = s.passed + s.failed + s.blocked + s.not_run;
            return total > 0 ? Math.round(s.passed / total * 100) : 0;
        });
        const openDefs = snapshots.map(s =>
            (s.open_defects_s1 || 0) + (s.open_defects_s2 || 0) + (s.open_defects_s3 || 0) + (s.open_defects_s4 || 0));

        new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Pass Rate %', data: passRates, borderColor: '#107e3e', backgroundColor: 'rgba(16,126,62,0.1)', fill: true, yAxisID: 'y', tension: 0.3 },
                    { label: 'Open Defects', data: openDefs, borderColor: '#c4314b', backgroundColor: 'rgba(196,49,75,0.1)', fill: false, yAxisID: 'y1', tension: 0.3 },
                ],
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, max: 100, position: 'left', title: { display: true, text: 'Pass Rate %' } },
                    y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Open Defects' } },
                },
                plugins: { legend: { position: 'bottom' } },
            },
        });
    }

    async function captureSnapshot() {
        const pid = TestingShared.pid;
        try {
            await API.post(`/programs/${pid}/testing/snapshots`, {});
            App.toast('Snapshot captured', 'success');
            await loadSnapshots();
        } catch(e) {
            App.toast('Failed to capture snapshot: ' + e.message, 'error');
        }
    }

    // ── Public API ─────────────────────────────────────────────────────────
    return {
        render,
        switchTab,
        // Plans & Cycles
        showPlanModal, savePlan, deletePlan,
        showCycleModal, saveCycle, deleteCycle,
        viewCycleExecs, showExecModal, saveExec, showExecEditModal, updateExec, deleteExec,
        // Runs
        viewCycleRuns, showNewRunModal, saveNewRun, openRunExecution,
        addStepResultRow, saveStepResults, updateRunStatus, completeRun, deleteRun,
        // Sign-off & Criteria
        showSignoffModal, createSignoff, updateSignoff, deleteSignoff,
        validateEntry, validateExit,
        // Go/No-Go & Snapshots
        loadGoNoGo, loadSnapshots, captureSnapshot,
    };
})();
