/**
 * SAP Transformation Management Platform
 * Requirement View — Sprint 3: Requirements management + traceability matrix.
 */

const RequirementView = (() => {
    let requirements = [];
    let currentReq = null;
    let programId = null;

    // ── Render requirement list ──────────────────────────────────────────
    async function render() {
        currentReq = null;
        const prog = App.getActiveProgram();
        programId = prog ? prog.id : null;
        const main = document.getElementById('mainContent');

        if (!programId) {
            main.innerHTML = `
                <div class="page-header"><h1>Requirements</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">📝</div>
                    <div class="empty-state__title">Select a Program</div>
                    <p>Go to <a href="#" onclick="App.navigate('programs');return false">Programs</a> to select one.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>Requirements</h1>
                <div>
                    <button class="btn btn-secondary" onclick="RequirementView.showMatrix()">🔗 Traceability Matrix</button>
                    <button class="btn btn-secondary" onclick="RequirementView.showStats()">📊 Stats</button>
                    <button class="btn btn-primary" onclick="RequirementView.showCreateModal()">+ New Requirement</button>
                </div>
            </div>
            <div class="card" style="margin-bottom:16px">
                <div class="req-filters" id="reqFilters">
                    <select id="filterType" class="form-input form-input--sm" onchange="RequirementView.applyFilters()">
                        <option value="">All Types</option>
                        <option value="business">Business</option>
                        <option value="functional">Functional</option>
                        <option value="technical">Technical</option>
                        <option value="non_functional">Non-Functional</option>
                        <option value="integration">Integration</option>
                    </select>
                    <select id="filterStatus" class="form-input form-input--sm" onchange="RequirementView.applyFilters()">
                        <option value="">All Statuses</option>
                        <option value="draft">Draft</option>
                        <option value="approved">Approved</option>
                        <option value="in_progress">In Progress</option>
                        <option value="implemented">Implemented</option>
                        <option value="verified">Verified</option>
                        <option value="deferred">Deferred</option>
                        <option value="rejected">Rejected</option>
                    </select>
                    <select id="filterPriority" class="form-input form-input--sm" onchange="RequirementView.applyFilters()">
                        <option value="">All Priorities</option>
                        <option value="must_have">Must Have</option>
                        <option value="should_have">Should Have</option>
                        <option value="could_have">Could Have</option>
                        <option value="wont_have">Won't Have</option>
                    </select>

                </div>
            </div>
            <div class="card">
                <div id="reqListContainer">
                    <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
                </div>
            </div>`;
        await loadRequirements();
    }

    function _getSelectedProgramId() {
        const prog = App.getActiveProgram();
        return prog ? prog.id : null;
    }

    async function loadRequirements() {
        try {
            requirements = await API.get(`/programs/${programId}/requirements`);
            renderList(requirements);
        } catch (err) {
            document.getElementById('reqListContainer').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
        }
    }

    function applyFilters() {
        const type = document.getElementById('filterType').value;
        const status = document.getElementById('filterStatus').value;
        const priority = document.getElementById('filterPriority').value;
        let filtered = requirements;
        if (type) filtered = filtered.filter(r => r.req_type === type);
        if (status) filtered = filtered.filter(r => r.status === status);
        if (priority) filtered = filtered.filter(r => r.priority === priority);
        renderList(filtered);
    }

    function renderList(reqs) {
        const c = document.getElementById('reqListContainer');
        if (reqs.length === 0) {
            c.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📝</div>
                    <div class="empty-state__title">No requirements found</div>
                    <p>Create your first requirement or adjust filters.</p><br>
                    <button class="btn btn-primary" onclick="RequirementView.showCreateModal()">+ New Requirement</button>
                </div>`;
            return;
        }

        c.innerHTML = `
            <table class="data-table">
                <thead><tr>
                    <th>Code</th><th>Title</th><th>Type</th><th>Module</th>
                    <th>Priority</th><th>Status</th><th>Effort</th><th>Open Items</th><th>🔗</th><th>Actions</th>
                </tr></thead>
                <tbody>
                    ${reqs.map(r => `
                        <tr>
                            <td><strong>${escHtml(r.code || '—')}</strong></td>
                            <td><a href="#" onclick="RequirementView.openDetail(${r.id});return false">${escHtml(r.title)}</a>${r.source === 'process_tree' ? ' <span title="Created from Process Tree" style="font-size:11px">🔗</span>' : ''}</td>
                            <td>${r.req_type}</td>
                            <td>${r.module || '—'}</td>
                            <td><span class="badge badge-${_priorityClass(r.priority)}">${r.priority}</span></td>
                            <td><span class="badge badge-${_statusClass(r.status)}">${r.status}</span></td>
                            <td>${r.effort_estimate || '—'}</td>
                            <td>${r.open_item_count ? `<span class="badge badge-warning">${r.open_item_count}</span>` : '—'} ${r.blocker_count ? `<span class="badge badge-danger">${r.blocker_count}B</span>` : ''}</td>
                            <td>${r.process_mapping_count ? `<span class="badge badge-info" title="${r.process_mapping_count} mapped L3 step(s)">🔗 ${r.process_mapping_count}</span>` : ''}</td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="RequirementView.openDetail(${r.id})">View</button>
                                <button class="btn btn-danger btn-sm" onclick="RequirementView.deleteReq(${r.id})">Delete</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    }

    function _priorityClass(p) {
        return { must_have: 'critical', should_have: 'high', could_have: 'medium', wont_have: 'low' }[p] || 'medium';
    }
    function _fitGapClass(f) {
        return { fit: 'passed', gap: 'failed', partial_fit: 'waived' }[f] || '';
    }
    function _statusClass(s) {
        return { draft: 'pending', approved: 'passed', in_progress: 'in_progress', implemented: 'passed', verified: 'passed', deferred: 'on_hold', rejected: 'failed' }[s] || '';
    }

    // ── Detail view ──────────────────────────────────────────────────────
    async function openDetail(id) {
        try {
            currentReq = await API.get(`/requirements/${id}`);
        } catch (err) { App.toast(err.message, 'error'); return; }
        renderDetail();
    }

    function renderDetail() {
        const r = currentReq;
        const main = document.getElementById('mainContent');

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="RequirementView.render()">← Back</button>
                    <h1 style="display:inline;margin-left:12px">${escHtml(r.code || '')} ${escHtml(r.title)}</h1>
                    <span class="badge badge-${_statusClass(r.status)}" style="margin-left:8px">${r.status}</span>
                </div>
                <button class="btn btn-primary" onclick="RequirementView.showEditModal()">Edit</button>
            </div>

            <div class="detail-grid">
                <div class="detail-section">
                    <h3>Classification</h3>
                    <dl class="detail-list">
                        <dt>Type</dt><dd>${r.req_type}</dd>
                        <dt>Priority</dt><dd><span class="badge badge-${_priorityClass(r.priority)}">${r.priority}</span></dd>
                        <dt>Module</dt><dd>${r.module || '—'}</dd>
                        <dt>Effort</dt><dd>${r.effort_estimate || '—'}</dd>
                        <dt>Source</dt><dd>${r.source || '—'}</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Description</h3>
                    <p>${escHtml(r.description || 'No description.')}</p>
                    ${r.acceptance_criteria ? `<h4 style="margin-top:12px">Acceptance Criteria</h4><p>${escHtml(r.acceptance_criteria)}</p>` : ''}
                    ${r.notes ? `<h4 style="margin-top:12px">Notes</h4><p>${escHtml(r.notes)}</p>` : ''}
                </div>
            </div>

            <div class="card" style="margin-top:20px">
                <div class="card-header">
                    <h3>Traceability Links</h3>
                    <button class="btn btn-primary btn-sm" onclick="RequirementView.showAddTraceModal()">+ Add Trace</button>
                </div>
                <div id="traceList"></div>
            </div>

            ${(r.process_mappings && r.process_mappings.length) ? `
            <div class="card" style="margin-top:20px">
                <div class="card-header">
                    <h3>🔗 Mapped L3 Process Steps</h3>
                    <button class="btn btn-primary btn-sm" onclick="RequirementView.showAddL3Modal()">+ Add L3 Step</button>
                </div>
                <table class="data-table">
                    <thead><tr><th>L3 Step</th><th>Coverage</th><th>Fit/Gap</th><th>SAP TCode</th><th>Notes</th></tr></thead>
                    <tbody>
                        ${r.process_mappings.map(m => `
                            <tr>
                                <td><strong>${escHtml(m.process_name || '—')}</strong></td>
                                <td><span class="badge badge-${m.coverage_type}">${m.coverage_type}</span></td>
                                <td>${m.process_fit_gap ? `<span class="badge badge-${m.process_fit_gap}">${m.process_fit_gap}</span>` : '—'}</td>
                                <td>${escHtml(m.process_sap_tcode || '—')}</td>
                                <td>${escHtml(m.notes || '—')}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>` : `
            <div class="card" style="margin-top:20px">
                <div class="card-header">
                    <h3>🔗 Mapped L3 Process Steps</h3>
                    <button class="btn btn-primary btn-sm" onclick="RequirementView.showAddL3Modal()">+ Add L3 Step</button>
                </div>
                <p style="color:var(--sap-text-secondary);padding:16px">No L3 process steps mapped yet. Create one to define the scope.</p>
            </div>`}

            <div class="card" style="margin-top:20px">
                <div class="card-header">
                    <h3>📌 Open Items</h3>
                    <button class="btn btn-primary btn-sm" onclick="RequirementView.showAddOpenItemModal()">+ Open Item</button>
                </div>
                <div id="openItemsList"></div>
            </div>

            ${(r.children && r.children.length) ? `
            <div class="card" style="margin-top:20px">
                <h3>Child Requirements</h3>
                <table class="data-table">
                    <thead><tr><th>Code</th><th>Title</th><th>Type</th><th>Status</th></tr></thead>
                    <tbody>
                        ${r.children.map(c => `
                            <tr style="cursor:pointer" onclick="RequirementView.openDetail(${c.id})">
                                <td>${escHtml(c.code || '—')}</td>
                                <td>${escHtml(c.title)}</td>
                                <td>${c.req_type}</td>
                                <td><span class="badge badge-${_statusClass(c.status)}">${c.status}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>` : ''}
        `;
        renderTraces();
        renderOpenItems();
    }

    function renderTraces() {
        const traces = currentReq.traces || [];
        const c = document.getElementById('traceList');
        if (traces.length === 0) {
            c.innerHTML = '<p style="color:var(--sap-text-secondary)">No traceability links.</p>';
            return;
        }
        c.innerHTML = `
            <table class="data-table">
                <thead><tr><th>Target Type</th><th>Target ID</th><th>Trace Type</th><th>Notes</th><th>Actions</th></tr></thead>
                <tbody>
                    ${traces.map(t => `
                        <tr>
                            <td><span class="badge">${t.target_type}</span></td>
                            <td>#${t.target_id}</td>
                            <td>${t.trace_type}</td>
                            <td>${escHtml(t.notes || '')}</td>
                            <td><button class="btn btn-danger btn-sm" onclick="RequirementView.deleteTrace(${t.id})">Remove</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    }

    // ── Traceability Matrix View ─────────────────────────────────────────
    async function showMatrix() {
        if (!programId) return;
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="RequirementView.render()">← Back</button>
                    <h1 style="display:inline;margin-left:12px">Traceability Matrix</h1>
                </div>
            </div>
            <div class="card" id="matrixContainer">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>`;

        try {
            const data = await API.get(`/programs/${programId}/traceability-matrix`);
            renderMatrix(data);
        } catch (err) {
            document.getElementById('matrixContainer').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
        }
    }

    function renderMatrix(data) {
        const container = document.getElementById('matrixContainer');
        const reqs = data.requirements || [];
        const phases = data.phases || [];
        const workstreams = data.workstreams || [];
        const matrix = data.matrix || {};

        if (reqs.length === 0) {
            container.innerHTML = '<p>No requirements to display in the matrix.</p>';
            return;
        }

        container.innerHTML = `
            <div style="overflow-x:auto">
                <table class="data-table matrix-table">
                    <thead>
                        <tr>
                            <th>Code</th>
                            <th>Title</th>
                            <th>Type</th>
                            <th>Priority</th>
                            ${phases.map(p => `<th class="matrix-col-header" title="${escHtml(p.name)}">${escHtml(p.name.substring(0, 8))}</th>`).join('')}
                            ${workstreams.map(w => `<th class="matrix-col-header ws-col" title="${escHtml(w.name)}">${escHtml(w.name.substring(0, 8))}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${reqs.map(r => {
                            const m = matrix[String(r.id)] || {};
                            return `<tr>
                                <td><strong>${escHtml(r.code || '—')}</strong></td>
                                <td>${escHtml(r.title)}</td>
                                <td>${r.req_type}</td>
                                <td><span class="badge badge-${_priorityClass(r.priority)}">${r.priority}</span></td>
                                ${phases.map(p => `<td class="matrix-cell">${(m.phase_ids || []).includes(p.id) ? '✓' : ''}</td>`).join('')}
                                ${workstreams.map(w => `<td class="matrix-cell ws-col">${(m.workstream_ids || []).includes(w.id) ? '✓' : ''}</td>`).join('')}
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>
            </div>
            <div style="margin-top:12px;font-size:0.85rem;color:var(--sap-text-secondary)">
                ✓ = traceability link exists &nbsp;|&nbsp;
                <span style="color:var(--sap-blue)">Blue columns</span> = Phases &nbsp;|&nbsp;
                <span style="color:var(--sap-positive)">Green columns</span> = Workstreams
            </div>`;
    }

    // ── Stats View ───────────────────────────────────────────────────────
    async function showStats() {
        if (!programId) return;
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="RequirementView.render()">← Back</button>
                    <h1 style="display:inline;margin-left:12px">Requirement Statistics</h1>
                </div>
            </div>
            <div id="statsContainer">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>`;

        try {
            const stats = await API.get(`/programs/${programId}/requirements/stats`);
            renderStats(stats);
        } catch (err) {
            document.getElementById('statsContainer').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
        }
    }

    function renderStats(stats) {
        const c = document.getElementById('statsContainer');

        c.innerHTML = `
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-card__value">${stats.total}</div>
                    <div class="kpi-card__label">Total Requirements</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${stats.total_open_items || 0}</div>
                    <div class="kpi-card__label">Open Items</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value" style="color:${(stats.blocker_open_items||0)>0?'#bb0000':'#30914c'}">${stats.blocker_open_items || 0}</div>
                    <div class="kpi-card__label">Blockers</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${stats.by_priority?.must_have || 0}</div>
                    <div class="kpi-card__label">Must Have</div>
                </div>
            </div>
            <div class="dashboard-grid" style="margin-top:20px">
                <div class="card">
                    <h3>By Type</h3>
                    <canvas id="reqTypeChart" height="220"></canvas>
                </div>
                <div class="card">
                    <h3>By Status</h3>
                    <canvas id="reqStatusChart" height="220"></canvas>
                </div>
            </div>
            <div class="dashboard-grid">
                <div class="card">
                    <h3>By Priority (MoSCoW)</h3>
                    <canvas id="reqPriorityChart" height="220"></canvas>
                </div>
                <div class="card">
                    <h3>By Module</h3>
                    <canvas id="reqModuleChart" height="220"></canvas>
                </div>
            </div>`;

        if (typeof Chart !== 'undefined') {
            _barChart('reqTypeChart', stats.by_type, '#0070f2');
            _barChart('reqStatusChart', stats.by_status, '#e76500');
            _barChart('reqPriorityChart', stats.by_priority, '#30914c');
            _barChart('reqModuleChart', stats.by_module, '#cc1919');
        }
    }

    function _barChart(canvasId, dataObj, color) {
        const labels = Object.keys(dataObj || {});
        const values = Object.values(dataObj || {});
        if (labels.length === 0) return;
        new Chart(document.getElementById(canvasId), {
            type: 'bar',
            data: {
                labels,
                datasets: [{ data: values, backgroundColor: color, borderRadius: 6 }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            },
        });
    }

    // ── Modals ───────────────────────────────────────────────────────────
    function showCreateModal() {
        App.openModal(`
            <div class="modal-header"><h2>New Requirement</h2></div>
            <div class="modal-body">
                <div class="form-row">
                    <div class="form-group"><label>Code</label><input id="rCode" class="form-input" placeholder="REQ-FI-001"></div>
                    <div class="form-group" style="flex:2"><label>Title *</label><input id="rTitle" class="form-input"></div>
                </div>
                <div class="form-group"><label>Description</label><textarea id="rDesc" class="form-input" rows="3"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label>
                        <select id="rType" class="form-input">
                            <option value="functional">Functional</option>
                            <option value="business">Business</option>
                            <option value="technical">Technical</option>
                            <option value="non_functional">Non-Functional</option>
                            <option value="integration">Integration</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Priority (MoSCoW)</label>
                        <select id="rPriority" class="form-input">
                            <option value="must_have">Must Have</option>
                            <option value="should_have">Should Have</option>
                            <option value="could_have" selected>Could Have</option>
                            <option value="wont_have">Won't Have</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Module</label>
                        <input id="rModule" class="form-input" placeholder="FI, CO, MM, SD...">
                    </div>
                    <div class="form-group"><label>Effort</label>
                        <select id="rEffort" class="form-input">
                            <option value="">—</option>
                            <option value="xs">XS</option>
                            <option value="s">S</option>
                            <option value="m">M</option>
                            <option value="l">L</option>
                            <option value="xl">XL</option>
                        </select>
                    </div>
                </div>
                <div class="form-group"><label>Source</label><input id="rSource" class="form-input" placeholder="Workshop, Business user..."></div>
                <div class="form-group"><label>Acceptance Criteria</label><textarea id="rAC" class="form-input" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="RequirementView.doCreate()">Create</button>
            </div>
        `);
    }

    async function doCreate() {
        const body = {
            code: document.getElementById('rCode').value,
            title: document.getElementById('rTitle').value,
            description: document.getElementById('rDesc').value,
            req_type: document.getElementById('rType').value,
            priority: document.getElementById('rPriority').value,
            module: document.getElementById('rModule').value,
            effort_estimate: document.getElementById('rEffort').value,
            source: document.getElementById('rSource').value,
            acceptance_criteria: document.getElementById('rAC').value,
        };
        try {
            await API.post(`/programs/${programId}/requirements`, body);
            App.closeModal();
            App.toast('Requirement created', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function showEditModal() {
        const r = currentReq;
        App.openModal(`
            <div class="modal-header"><h2>Edit Requirement</h2></div>
            <div class="modal-body">
                <div class="form-row">
                    <div class="form-group"><label>Code</label><input id="rCode" class="form-input" value="${escAttr(r.code)}"></div>
                    <div class="form-group" style="flex:2"><label>Title *</label><input id="rTitle" class="form-input" value="${escAttr(r.title)}"></div>
                </div>
                <div class="form-group"><label>Description</label><textarea id="rDesc" class="form-input" rows="3">${escHtml(r.description||'')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label>
                        <select id="rType" class="form-input">
                            ${['functional','business','technical','non_functional','integration'].map(t => `<option value="${t}" ${r.req_type===t?'selected':''}>${t}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Priority</label>
                        <select id="rPriority" class="form-input">
                            ${['must_have','should_have','could_have','wont_have'].map(p => `<option value="${p}" ${r.priority===p?'selected':''}>${p}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Status</label>
                        <select id="rStatus" class="form-input">
                            ${['draft','approved','in_progress','implemented','verified','deferred','rejected'].map(st => `<option value="${st}" ${r.status===st?'selected':''}>${st}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Module</label><input id="rModule" class="form-input" value="${escAttr(r.module)}"></div>
                    <div class="form-group"><label>Effort</label>
                        <select id="rEffort" class="form-input">
                            ${['','xs','s','m','l','xl'].map(e => `<option value="${e}" ${r.effort_estimate===e?'selected':''}>${e||'—'}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-group"><label>Source</label><input id="rSource" class="form-input" value="${escAttr(r.source)}"></div>
                <div class="form-group"><label>Acceptance Criteria</label><textarea id="rAC" class="form-input" rows="2">${escHtml(r.acceptance_criteria||'')}</textarea></div>
                <div class="form-group"><label>Notes</label><textarea id="rNotes" class="form-input" rows="2">${escHtml(r.notes||'')}</textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="RequirementView.doEdit()">Save</button>
            </div>
        `);
    }

    async function doEdit() {
        const body = {
            code: document.getElementById('rCode').value,
            title: document.getElementById('rTitle').value,
            description: document.getElementById('rDesc').value,
            req_type: document.getElementById('rType').value,
            priority: document.getElementById('rPriority').value,
            status: document.getElementById('rStatus').value,
            module: document.getElementById('rModule').value,
            effort_estimate: document.getElementById('rEffort').value,
            source: document.getElementById('rSource').value,
            acceptance_criteria: document.getElementById('rAC').value,
            notes: document.getElementById('rNotes').value,
        };
        try {
            await API.put(`/requirements/${currentReq.id}`, body);
            App.closeModal();
            App.toast('Requirement updated', 'success');
            await openDetail(currentReq.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteReq(id) {
        if (!confirm('Delete this requirement?')) return;
        try {
            await API.delete(`/requirements/${id}`);
            App.toast('Requirement deleted', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Trace modals ─────────────────────────────────────────────────────
    function showAddTraceModal() {
        App.openModal(`
            <div class="modal-header"><h2>Add Traceability Link</h2></div>
            <div class="modal-body">
                <div class="form-row">
                    <div class="form-group"><label>Target Type *</label>
                        <select id="tTargetType" class="form-input">
                            <option value="phase">Phase</option>
                            <option value="workstream">Workstream</option>
                            <option value="scenario">Scenario</option>
                            <option value="requirement">Requirement</option>
                            <option value="gate">Gate</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Target ID *</label>
                        <input id="tTargetId" type="number" class="form-input">
                    </div>
                </div>
                <div class="form-group"><label>Trace Type</label>
                    <select id="tTraceType" class="form-input">
                        <option value="implements">Implements</option>
                        <option value="depends_on">Depends On</option>
                        <option value="derived_from">Derived From</option>
                        <option value="tested_by">Tested By</option>
                        <option value="related_to">Related To</option>
                    </select>
                </div>
                <div class="form-group"><label>Notes</label><input id="tNotes" class="form-input"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="RequirementView.doAddTrace()">Add Link</button>
            </div>
        `);
    }

    async function doAddTrace() {
        const body = {
            target_type: document.getElementById('tTargetType').value,
            target_id: parseInt(document.getElementById('tTargetId').value),
            trace_type: document.getElementById('tTraceType').value,
            notes: document.getElementById('tNotes').value,
        };
        try {
            await API.post(`/requirements/${currentReq.id}/traces`, body);
            App.closeModal();
            App.toast('Trace added', 'success');
            await openDetail(currentReq.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteTrace(id) {
        if (!confirm('Remove this traceability link?')) return;
        try {
            await API.delete(`/requirement-traces/${id}`);
            App.toast('Trace removed', 'success');
            await openDetail(currentReq.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Open Items ────────────────────────────────────────────────────────
    async function renderOpenItems() {
        const c = document.getElementById('openItemsList');
        if (!c) return;
        try {
            const items = await API.get(`/requirements/${currentReq.id}/open-items`);
            if (!items.length) { c.innerHTML = '<p style="color:var(--sap-text-secondary);padding:8px">No open items.</p>'; return; }
            c.innerHTML = `<table class="data-table"><thead><tr><th>Title</th><th>Type</th><th>Status</th><th>Priority</th><th>Owner</th><th>Blocker</th><th>Actions</th></tr></thead><tbody>${items.map(i => `<tr><td><strong>${escHtml(i.title)}</strong>${i.description?`<br><small style="color:var(--sap-text-secondary)">${escHtml(i.description.substring(0,80))}</small>`:''}</td><td><span class="badge">${i.item_type}</span></td><td><span class="badge badge-${i.status==='resolved'||i.status==='closed'?'passed':i.status==='in_progress'?'in_progress':'pending'}">${i.status}</span></td><td><span class="badge badge-priority-${i.priority}">${i.priority}</span></td><td>${escHtml(i.owner||'—')}</td><td>${i.blocker?'<span class="badge badge-danger">BLOCKER</span>':'—'}</td><td><button class="btn btn-secondary btn-sm" onclick="RequirementView.showEditOpenItemModal(${i.id})">Edit</button> <button class="btn btn-danger btn-sm" onclick="RequirementView.deleteOpenItem(${i.id})">Del</button></td></tr>`).join('')}</tbody></table>`;
        } catch(e) { c.innerHTML = `<p>⚠️ ${e.message}</p>`; }
    }

    function showAddOpenItemModal() {
        App.openModal(`
            <div class="modal-header"><h2>Add Open Item</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Title *</label><input id="oiTitle" class="form-input"></div>
                <div class="form-group"><label>Description</label><textarea id="oiDesc" class="form-input" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label><select id="oiType" class="form-input"><option value="question">Question</option><option value="decision">Decision</option><option value="dependency">Dependency</option><option value="escalation">Escalation</option></select></div>
                    <div class="form-group"><label>Priority</label><select id="oiPrio" class="form-input"><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option><option value="low">Low</option></select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Owner</label><input id="oiOwner" class="form-input"></div>
                    <div class="form-group"><label>Due Date</label><input id="oiDue" type="date" class="form-input"></div>
                </div>
                <div class="form-group"><label><input type="checkbox" id="oiBlocker"> Blocker</label></div>
            </div>
            <div class="modal-footer"><button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button><button class="btn btn-primary" onclick="RequirementView.doAddOpenItem()">Create</button></div>`);
    }

    async function doAddOpenItem() {
        try {
            await API.post(`/requirements/${currentReq.id}/open-items`, {
                title: document.getElementById('oiTitle').value,
                description: document.getElementById('oiDesc').value,
                item_type: document.getElementById('oiType').value,
                priority: document.getElementById('oiPrio').value,
                owner: document.getElementById('oiOwner').value,
                due_date: document.getElementById('oiDue').value || null,
                blocker: document.getElementById('oiBlocker').checked,
            });
            App.closeModal(); App.toast('Open item created','success'); await renderOpenItems();
        } catch(e) { App.toast(e.message,'error'); }
    }

    function showEditOpenItemModal(id) {
        API.get(`/open-items/${id}`).then(i => {
            App.openModal(`
                <div class="modal-header"><h2>Edit Open Item</h2></div>
                <div class="modal-body">
                    <div class="form-group"><label>Title *</label><input id="oiTitle" class="form-input" value="${escAttr(i.title)}"></div>
                    <div class="form-group"><label>Description</label><textarea id="oiDesc" class="form-input" rows="2">${escHtml(i.description||'')}</textarea></div>
                    <div class="form-row">
                        <div class="form-group"><label>Type</label><select id="oiType" class="form-input">${['question','decision','dependency','escalation'].map(t=>`<option value="${t}" ${i.item_type===t?'selected':''}>${t}</option>`).join('')}</select></div>
                        <div class="form-group"><label>Status</label><select id="oiStatus" class="form-input">${['open','in_progress','resolved','closed'].map(s=>`<option value="${s}" ${i.status===s?'selected':''}>${s}</option>`).join('')}</select></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Priority</label><select id="oiPrio" class="form-input">${['low','medium','high','critical'].map(p=>`<option value="${p}" ${i.priority===p?'selected':''}>${p}</option>`).join('')}</select></div>
                        <div class="form-group"><label>Owner</label><input id="oiOwner" class="form-input" value="${escAttr(i.owner)}"></div>
                    </div>
                    <div class="form-group"><label>Due Date</label><input id="oiDue" type="date" class="form-input" value="${i.due_date||''}"></div>
                    <div class="form-group"><label>Resolution</label><textarea id="oiRes" class="form-input" rows="2">${escHtml(i.resolution||'')}</textarea></div>
                    <div class="form-group"><label><input type="checkbox" id="oiBlocker" ${i.blocker?'checked':''}> Blocker</label></div>
                </div>
                <div class="modal-footer"><button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button><button class="btn btn-primary" onclick="RequirementView.doEditOpenItem(${id})">Save</button></div>`);
        }).catch(e => App.toast(e.message,'error'));
    }

    async function doEditOpenItem(id) {
        try {
            await API.put(`/open-items/${id}`, {
                title: document.getElementById('oiTitle').value,
                description: document.getElementById('oiDesc').value,
                item_type: document.getElementById('oiType').value,
                status: document.getElementById('oiStatus').value,
                priority: document.getElementById('oiPrio').value,
                owner: document.getElementById('oiOwner').value,
                due_date: document.getElementById('oiDue').value || null,
                resolution: document.getElementById('oiRes').value,
                blocker: document.getElementById('oiBlocker').checked,
            });
            App.closeModal(); App.toast('Updated','success'); await renderOpenItems();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function deleteOpenItem(id) {
        if (!confirm('Delete this open item?')) return;
        try { await API.delete(`/open-items/${id}`); App.toast('Deleted','success'); await renderOpenItems(); }
        catch(e) { App.toast(e.message,'error'); }
    }

    // ── Add L3 Process Step from Requirement ─────────────────────────────
    function showAddL3Modal() {
        if (!currentReq || !currentReq.process_id) {
            App.toast('This requirement has no L2 process assigned. Edit the requirement first and set a process.', 'error');
            return;
        }
        App.openModal(`
            <div class="modal-header"><h2>Add L3 Process Step</h2></div>
            <div class="modal-body">
                <p style="margin-bottom:12px;color:var(--sap-text-secondary)">
                    Creates a new L3 step under this requirement's L2 process and automatically links it.
                </p>
                <div class="form-group"><label>Name *</label><input id="l3Name" class="form-input" placeholder="e.g. Standard Sales Order (VA01)"></div>
                <div class="form-group"><label>Description</label><textarea id="l3Desc" class="form-input" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Code</label><input id="l3Code" class="form-input" placeholder="e.g. 1OC"></div>
                    <div class="form-group"><label>SAP TCode</label><input id="l3TCode" class="form-input" placeholder="e.g. VA01"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Scope Decision</label>
                        <select id="l3Scope" class="form-input">
                            <option value="in_scope" selected>In Scope</option>
                            <option value="out_of_scope">Out of Scope</option>
                            <option value="deferred">Deferred</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Fit/Gap</label>
                        <select id="l3FitGap" class="form-input">
                            <option value="">— Not Set —</option>
                            <option value="fit">Fit</option>
                            <option value="gap">Gap</option>
                            <option value="partial_fit">Partial Fit</option>
                            <option value="standard">Standard</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Priority</label>
                        <select id="l3Priority" class="form-input">
                            <option value="medium" selected>Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                            <option value="low">Low</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Coverage</label>
                        <select id="l3Coverage" class="form-input">
                            <option value="full" selected>Full</option>
                            <option value="partial">Partial</option>
                            <option value="none">None</option>
                        </select>
                    </div>
                </div>
                <div class="form-group"><label>Notes</label><textarea id="l3Notes" class="form-input" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="RequirementView.doAddL3()">Create L3 Step</button>
            </div>
        `);
    }

    async function doAddL3() {
        const body = {
            name: document.getElementById('l3Name').value,
            description: document.getElementById('l3Desc').value,
            code: document.getElementById('l3Code').value,
            sap_tcode: document.getElementById('l3TCode').value,
            scope_decision: document.getElementById('l3Scope').value,
            fit_gap: document.getElementById('l3FitGap').value,
            priority: document.getElementById('l3Priority').value,
            coverage_type: document.getElementById('l3Coverage').value,
            notes: document.getElementById('l3Notes').value,
        };
        try {
            await API.post(`/requirements/${currentReq.id}/create-l3`, body);
            App.closeModal();
            App.toast('L3 Process Step created and mapped', 'success');
            await openDetail(currentReq.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Utility ──────────────────────────────────────────────────────────
    function escHtml(s) {
        const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
    }
    function escAttr(s) { return (s || '').replace(/"/g, '&quot;'); }

    return {
        render, openDetail, showCreateModal, doCreate, showEditModal, doEdit,
        deleteReq, showMatrix, showStats, applyFilters,
        showAddTraceModal, doAddTrace, deleteTrace,
        showAddOpenItemModal, doAddOpenItem, showEditOpenItemModal, doEditOpenItem, deleteOpenItem,
        showAddL3Modal, doAddL3,
    };
})();
