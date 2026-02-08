/**
 * SAP Transformation Management Platform
 * Scenario View — Sprint 3: What-if analysis & scenario comparison.
 */

const ScenarioView = (() => {
    let scenarios = [];
    let currentScenario = null;
    let programId = null;

    // ── Render scenario list ─────────────────────────────────────────────
    async function render() {
        currentScenario = null;
        programId = _getSelectedProgramId();
        const main = document.getElementById('mainContent');

        if (!programId) {
            main.innerHTML = `
                <div class="page-header"><h1>Scenarios</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">🎯</div>
                    <div class="empty-state__title">Select a Program</div>
                    <p>Choose a program from the header dropdown to view its scenarios.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>Scenarios</h1>
                <div>
                    <button class="btn btn-secondary" onclick="ScenarioView.showCompare()">📊 Compare</button>
                    <button class="btn btn-primary" onclick="ScenarioView.showCreateModal()">+ New Scenario</button>
                </div>
            </div>
            <div class="card">
                <div id="scenarioListContainer">
                    <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
                </div>
            </div>`;
        await loadScenarios();
    }

    function _getSelectedProgramId() {
        const sel = document.getElementById('globalProjectSelector');
        return sel ? parseInt(sel.value) || null : null;
    }

    async function loadScenarios() {
        try {
            scenarios = await API.get(`/programs/${programId}/scenarios`);
            renderList();
        } catch (err) {
            document.getElementById('scenarioListContainer').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
        }
    }

    function renderList() {
        const c = document.getElementById('scenarioListContainer');
        if (scenarios.length === 0) {
            c.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🎯</div>
                    <div class="empty-state__title">No scenarios yet</div>
                    <p>Create your first what-if scenario to compare transformation approaches.</p><br>
                    <button class="btn btn-primary" onclick="ScenarioView.showCreateModal()">+ New Scenario</button>
                </div>`;
            return;
        }

        c.innerHTML = `
            <div class="scenario-grid">
                ${scenarios.map(s => `
                    <div class="scenario-card ${s.is_baseline ? 'scenario-card--baseline' : ''}">
                        <div class="scenario-card__header">
                            <h3>${escHtml(s.name)}</h3>
                            ${s.is_baseline ? '<span class="badge badge-passed">★ Baseline</span>' : ''}
                            <span class="badge badge-${s.status}">${s.status}</span>
                        </div>
                        <p class="scenario-card__desc">${escHtml(s.description || '—')}</p>
                        <div class="scenario-card__meta">
                            <div class="scenario-meta-item">
                                <span class="meta-label">Type</span>
                                <span>${s.scenario_type}</span>
                            </div>
                            <div class="scenario-meta-item">
                                <span class="meta-label">Duration</span>
                                <span>${s.estimated_duration_weeks ? s.estimated_duration_weeks + ' weeks' : '—'}</span>
                            </div>
                            <div class="scenario-meta-item">
                                <span class="meta-label">Cost</span>
                                <span>${s.estimated_cost ? '€' + Number(s.estimated_cost).toLocaleString() : '—'}</span>
                            </div>
                            <div class="scenario-meta-item">
                                <span class="meta-label">Resources</span>
                                <span>${s.estimated_resources || '—'}</span>
                            </div>
                            <div class="scenario-meta-item">
                                <span class="meta-label">Risk</span>
                                <span class="badge badge-${s.risk_level}">${s.risk_level}</span>
                            </div>
                            <div class="scenario-meta-item">
                                <span class="meta-label">Confidence</span>
                                <span>${s.confidence_pct}%</span>
                            </div>
                        </div>
                        <div class="scenario-card__actions">
                            <button class="btn btn-secondary btn-sm" onclick="ScenarioView.openDetail(${s.id})">View</button>
                            ${!s.is_baseline ? `<button class="btn btn-sm" style="background:#30914c;color:#fff" onclick="ScenarioView.setBaseline(${s.id})">Set Baseline</button>` : ''}
                            <button class="btn btn-danger btn-sm" onclick="ScenarioView.deleteScenario(${s.id})">Delete</button>
                        </div>
                    </div>
                `).join('')}
            </div>`;
    }

    // ── Detail view ──────────────────────────────────────────────────────
    async function openDetail(id) {
        try {
            currentScenario = await API.get(`/scenarios/${id}`);
        } catch (err) { App.toast(err.message, 'error'); return; }
        renderDetail();
    }

    function renderDetail() {
        const s = currentScenario;
        const main = document.getElementById('mainContent');
        const prosLines = (s.pros || '').split('\n').filter(l => l.trim());
        const consLines = (s.cons || '').split('\n').filter(l => l.trim());
        const assumptionLines = (s.assumptions || '').split('\n').filter(l => l.trim());

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="ScenarioView.render()">← Back</button>
                    <h1 style="display:inline;margin-left:12px">${escHtml(s.name)}</h1>
                    ${s.is_baseline ? '<span class="badge badge-passed" style="margin-left:8px">★ Baseline</span>' : ''}
                    <span class="badge badge-${s.status}" style="margin-left:8px">${s.status}</span>
                </div>
                <button class="btn btn-primary" onclick="ScenarioView.showEditModal()">Edit</button>
            </div>

            <div class="detail-grid">
                <div class="detail-section">
                    <h3>General</h3>
                    <dl class="detail-list">
                        <dt>Type</dt><dd>${s.scenario_type}</dd>
                        <dt>Risk</dt><dd><span class="badge badge-${s.risk_level}">${s.risk_level}</span></dd>
                        <dt>Confidence</dt><dd>${s.confidence_pct}%</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Estimates</h3>
                    <dl class="detail-list">
                        <dt>Duration</dt><dd>${s.estimated_duration_weeks ? s.estimated_duration_weeks + ' weeks' : '—'}</dd>
                        <dt>Cost</dt><dd>${s.estimated_cost ? '€' + Number(s.estimated_cost).toLocaleString() : '—'}</dd>
                        <dt>Resources</dt><dd>${s.estimated_resources || '—'}</dd>
                    </dl>
                </div>
            </div>

            <div class="card" style="margin-top:20px">
                <h3>Description</h3>
                <p>${escHtml(s.description || 'No description.')}</p>
            </div>

            <div class="detail-grid" style="margin-top:20px">
                <div class="card">
                    <h3 style="color:var(--sap-positive)">Pros</h3>
                    ${prosLines.length ? '<ul>' + prosLines.map(l => `<li>${escHtml(l)}</li>`).join('') + '</ul>' : '<p>—</p>'}
                </div>
                <div class="card">
                    <h3 style="color:var(--sap-negative)">Cons</h3>
                    ${consLines.length ? '<ul>' + consLines.map(l => `<li>${escHtml(l)}</li>`).join('') + '</ul>' : '<p>—</p>'}
                </div>
            </div>

            <div class="card" style="margin-top:20px">
                <h3>Assumptions</h3>
                ${assumptionLines.length ? '<ul>' + assumptionLines.map(l => `<li>${escHtml(l)}</li>`).join('') + '</ul>' : '<p>—</p>'}
            </div>

            ${s.recommendation ? `
            <div class="card" style="margin-top:20px">
                <h3>Recommendation</h3>
                <p>${escHtml(s.recommendation)}</p>
            </div>` : ''}

            <div class="card" style="margin-top:20px">
                <div class="card-header">
                    <h3>Parameters</h3>
                    <button class="btn btn-primary btn-sm" onclick="ScenarioView.showAddParamModal()">+ Add Parameter</button>
                </div>
                <div id="paramList"></div>
            </div>`;

        renderParams();
    }

    function renderParams() {
        const params = currentScenario.parameters || [];
        const c = document.getElementById('paramList');
        if (params.length === 0) {
            c.innerHTML = '<p style="color:var(--sap-text-secondary)">No parameters defined.</p>';
            return;
        }
        // Group by category
        const grouped = {};
        params.forEach(p => {
            (grouped[p.category] = grouped[p.category] || []).push(p);
        });
        c.innerHTML = Object.entries(grouped).map(([cat, items]) => `
            <div style="margin-bottom:16px">
                <h4 style="text-transform:capitalize;margin-bottom:8px">${cat}</h4>
                <table class="data-table">
                    <thead><tr><th>Key</th><th>Value</th><th>Notes</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${items.map(p => `
                            <tr>
                                <td><strong>${escHtml(p.key)}</strong></td>
                                <td>${escHtml(p.value)}</td>
                                <td>${escHtml(p.notes || '')}</td>
                                <td><button class="btn btn-danger btn-sm" onclick="ScenarioView.deleteParam(${p.id})">Delete</button></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `).join('');
    }

    // ── Compare view ─────────────────────────────────────────────────────
    async function showCompare() {
        if (!programId) return;
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="ScenarioView.render()">← Back</button>
                    <h1 style="display:inline;margin-left:12px">Scenario Comparison</h1>
                </div>
            </div>
            <div class="card" id="compareContainer">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>`;

        try {
            const data = await API.get(`/programs/${programId}/scenarios/compare`);
            renderCompare(data);
        } catch (err) {
            document.getElementById('compareContainer').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
        }
    }

    function renderCompare(data) {
        const container = document.getElementById('compareContainer');
        const scs = data.scenarios || [];
        if (scs.length === 0) {
            container.innerHTML = '<p>No scenarios to compare.</p>';
            return;
        }

        const keys = data.parameter_keys || [];
        const fixedRows = [
            { label: 'Type', fn: s => s.scenario_type },
            { label: 'Status', fn: s => `<span class="badge badge-${s.status}">${s.status}</span>` },
            { label: 'Duration', fn: s => s.estimated_duration_weeks ? s.estimated_duration_weeks + 'w' : '—' },
            { label: 'Cost', fn: s => s.estimated_cost ? '€' + Number(s.estimated_cost).toLocaleString() : '—' },
            { label: 'Resources', fn: s => s.estimated_resources || '—' },
            { label: 'Risk', fn: s => `<span class="badge badge-${s.risk_level}">${s.risk_level}</span>` },
            { label: 'Confidence', fn: s => s.confidence_pct + '%' },
        ];

        container.innerHTML = `
            <div style="overflow-x:auto">
                <table class="data-table compare-table">
                    <thead>
                        <tr>
                            <th></th>
                            ${scs.map(s => `<th>${escHtml(s.name)} ${s.is_baseline ? '★' : ''}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${fixedRows.map(row => `
                            <tr>
                                <td><strong>${row.label}</strong></td>
                                ${scs.map(s => `<td>${row.fn(s)}</td>`).join('')}
                            </tr>
                        `).join('')}
                        ${keys.length ? '<tr><td colspan="' + (scs.length + 1) + '" style="background:var(--sap-blue-light);font-weight:700">Parameters</td></tr>' : ''}
                        ${keys.map(k => `
                            <tr>
                                <td><strong>${escHtml(k)}</strong></td>
                                ${scs.map(s => `<td>${escHtml((s.parameter_map || {})[k] || '—')}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`;
    }

    // ── Modals ───────────────────────────────────────────────────────────
    function showCreateModal() {
        App.openModal(`
            <div class="modal-header"><h2>New Scenario</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label><input id="sName" class="form-input"></div>
                <div class="form-group"><label>Description</label><textarea id="sDesc" class="form-input" rows="3"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label>
                        <select id="sType" class="form-input">
                            <option value="approach">Approach</option>
                            <option value="timeline">Timeline</option>
                            <option value="scope">Scope</option>
                            <option value="cost">Cost</option>
                            <option value="resource">Resource</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Risk Level</label>
                        <select id="sRisk" class="form-input">
                            <option value="low">Low</option>
                            <option value="medium" selected>Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Duration (weeks)</label><input id="sDuration" type="number" class="form-input"></div>
                    <div class="form-group"><label>Est. Cost (€)</label><input id="sCost" type="number" class="form-input"></div>
                    <div class="form-group"><label>Resources (#)</label><input id="sResources" type="number" class="form-input"></div>
                </div>
                <div class="form-group"><label>Confidence (%)</label><input id="sConf" type="number" class="form-input" value="50" min="0" max="100"></div>
                <div class="form-group"><label>Pros (one per line)</label><textarea id="sPros" class="form-input" rows="3"></textarea></div>
                <div class="form-group"><label>Cons (one per line)</label><textarea id="sCons" class="form-input" rows="3"></textarea></div>
                <div class="form-group"><label>Assumptions (one per line)</label><textarea id="sAssumptions" class="form-input" rows="3"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ScenarioView.doCreate()">Create</button>
            </div>
        `);
    }

    async function doCreate() {
        const body = {
            name: document.getElementById('sName').value,
            description: document.getElementById('sDesc').value,
            scenario_type: document.getElementById('sType').value,
            risk_level: document.getElementById('sRisk').value,
            estimated_duration_weeks: parseInt(document.getElementById('sDuration').value) || null,
            estimated_cost: parseFloat(document.getElementById('sCost').value) || null,
            estimated_resources: parseInt(document.getElementById('sResources').value) || null,
            confidence_pct: parseInt(document.getElementById('sConf').value) || 50,
            pros: document.getElementById('sPros').value,
            cons: document.getElementById('sCons').value,
            assumptions: document.getElementById('sAssumptions').value,
        };
        try {
            await API.post(`/programs/${programId}/scenarios`, body);
            App.closeModal();
            App.toast('Scenario created', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function showEditModal() {
        const s = currentScenario;
        App.openModal(`
            <div class="modal-header"><h2>Edit Scenario</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label><input id="sName" class="form-input" value="${escAttr(s.name)}"></div>
                <div class="form-group"><label>Description</label><textarea id="sDesc" class="form-input" rows="3">${escHtml(s.description || '')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label>
                        <select id="sType" class="form-input">
                            ${['approach','timeline','scope','cost','resource'].map(t => `<option value="${t}" ${s.scenario_type===t?'selected':''}>${t}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Status</label>
                        <select id="sStatus" class="form-input">
                            ${['draft','under_review','approved','rejected','archived'].map(st => `<option value="${st}" ${s.status===st?'selected':''}>${st}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Risk</label>
                        <select id="sRisk" class="form-input">
                            ${['low','medium','high','critical'].map(r => `<option value="${r}" ${s.risk_level===r?'selected':''}>${r}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Duration (weeks)</label><input id="sDuration" type="number" class="form-input" value="${s.estimated_duration_weeks||''}"></div>
                    <div class="form-group"><label>Est. Cost (€)</label><input id="sCost" type="number" class="form-input" value="${s.estimated_cost||''}"></div>
                    <div class="form-group"><label>Resources (#)</label><input id="sResources" type="number" class="form-input" value="${s.estimated_resources||''}"></div>
                </div>
                <div class="form-group"><label>Confidence (%)</label><input id="sConf" type="number" class="form-input" value="${s.confidence_pct}" min="0" max="100"></div>
                <div class="form-group"><label>Pros</label><textarea id="sPros" class="form-input" rows="3">${escHtml(s.pros||'')}</textarea></div>
                <div class="form-group"><label>Cons</label><textarea id="sCons" class="form-input" rows="3">${escHtml(s.cons||'')}</textarea></div>
                <div class="form-group"><label>Assumptions</label><textarea id="sAssumptions" class="form-input" rows="3">${escHtml(s.assumptions||'')}</textarea></div>
                <div class="form-group"><label>Recommendation</label><textarea id="sRec" class="form-input" rows="3">${escHtml(s.recommendation||'')}</textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ScenarioView.doEdit()">Save</button>
            </div>
        `);
    }

    async function doEdit() {
        const body = {
            name: document.getElementById('sName').value,
            description: document.getElementById('sDesc').value,
            scenario_type: document.getElementById('sType').value,
            status: document.getElementById('sStatus').value,
            risk_level: document.getElementById('sRisk').value,
            estimated_duration_weeks: parseInt(document.getElementById('sDuration').value) || null,
            estimated_cost: parseFloat(document.getElementById('sCost').value) || null,
            estimated_resources: parseInt(document.getElementById('sResources').value) || null,
            confidence_pct: parseInt(document.getElementById('sConf').value) || 50,
            pros: document.getElementById('sPros').value,
            cons: document.getElementById('sCons').value,
            assumptions: document.getElementById('sAssumptions').value,
            recommendation: document.getElementById('sRec').value,
        };
        try {
            await API.put(`/scenarios/${currentScenario.id}`, body);
            App.closeModal();
            App.toast('Scenario updated', 'success');
            await openDetail(currentScenario.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function setBaseline(id) {
        try {
            await API.post(`/scenarios/${id}/set-baseline`, {});
            App.toast('Baseline set', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteScenario(id) {
        if (!confirm('Delete this scenario?')) return;
        try {
            await API.delete(`/scenarios/${id}`);
            App.toast('Scenario deleted', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Parameter modals ─────────────────────────────────────────────────
    function showAddParamModal() {
        App.openModal(`
            <div class="modal-header"><h2>Add Parameter</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Key *</label><input id="pKey" class="form-input" placeholder="e.g. deployment_model"></div>
                <div class="form-group"><label>Value</label><input id="pValue" class="form-input"></div>
                <div class="form-group"><label>Category</label>
                    <select id="pCat" class="form-input">
                        <option value="general">General</option>
                        <option value="technical">Technical</option>
                        <option value="financial">Financial</option>
                        <option value="organizational">Organizational</option>
                        <option value="timeline">Timeline</option>
                    </select>
                </div>
                <div class="form-group"><label>Notes</label><input id="pNotes" class="form-input"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ScenarioView.doAddParam()">Add</button>
            </div>
        `);
    }

    async function doAddParam() {
        const body = {
            key: document.getElementById('pKey').value,
            value: document.getElementById('pValue').value,
            category: document.getElementById('pCat').value,
            notes: document.getElementById('pNotes').value,
        };
        try {
            await API.post(`/scenarios/${currentScenario.id}/parameters`, body);
            App.closeModal();
            App.toast('Parameter added', 'success');
            await openDetail(currentScenario.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteParam(id) {
        if (!confirm('Delete this parameter?')) return;
        try {
            await API.delete(`/scenario-parameters/${id}`);
            App.toast('Parameter removed', 'success');
            await openDetail(currentScenario.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Utility ──────────────────────────────────────────────────────────
    function escHtml(s) {
        const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
    }
    function escAttr(s) { return (s || '').replace(/"/g, '&quot;'); }

    return {
        render, openDetail, showCreateModal, doCreate, showEditModal, doEdit,
        showCompare, setBaseline, deleteScenario,
        showAddParamModal, doAddParam, deleteParam,
    };
})();
