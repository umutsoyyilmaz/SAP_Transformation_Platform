/**
 * SAP Transformation Platform — RAID View (Sprint 6)
 *
 * Dashboard with risk heatmap, RAID stats, action aging
 * + tabbed list views (Risks / Actions / Issues / Decisions) with filters
 * + detail modals for create/edit
 */
const RaidView = (() => {
    let _programId = null;

    // ── Main Render ──────────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const sel = document.getElementById('globalProjectSelector');
        _programId = sel?.value || null;

        if (!_programId) {
            main.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">⚠️</div>
                    <div class="empty-state__title">RAID Log</div>
                    <p>Please select a programme from the header dropdown first.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h2>⚠️ RAID Log</h2>
                <div class="page-header__actions">
                    <button class="btn btn-primary" onclick="RaidView.openCreate('risk')">+ Risk</button>
                    <button class="btn btn-secondary" onclick="RaidView.openCreate('action')">+ Action</button>
                    <button class="btn btn-secondary" onclick="RaidView.openCreate('issue')">+ Issue</button>
                    <button class="btn btn-secondary" onclick="RaidView.openCreate('decision')">+ Decision</button>
                </div>
            </div>

            <!-- Stats Cards -->
            <div id="raidStats" class="kpi-grid" style="margin-bottom:1.5rem"></div>

            <!-- Heatmap -->
            <div class="card" style="margin-bottom:1.5rem">
                <div class="card__header"><h3>Risk Heatmap (Probability × Impact)</h3></div>
                <div class="card__body" id="riskHeatmap" style="overflow-x:auto"></div>
            </div>

            <!-- Tabs -->
            <div class="tabs" style="margin-bottom:1rem">
                <button class="tab active" data-tab="risks" onclick="RaidView.switchTab('risks')">🔴 Risks</button>
                <button class="tab" data-tab="actions" onclick="RaidView.switchTab('actions')">📋 Actions</button>
                <button class="tab" data-tab="issues" onclick="RaidView.switchTab('issues')">🔥 Issues</button>
                <button class="tab" data-tab="decisions" onclick="RaidView.switchTab('decisions')">📝 Decisions</button>
            </div>

            <div id="raidListContainer"></div>
        `;

        await Promise.all([loadStats(), loadHeatmap(), loadList('risks')]);
    }

    // ── Stats ────────────────────────────────────────────────────────────
    async function loadStats() {
        try {
            const s = await API.get(`/programs/${_programId}/raid/stats`);
            document.getElementById('raidStats').innerHTML = `
                <div class="kpi-card">
                    <div class="kpi-card__value">${s.risks.open}</div>
                    <div class="kpi-card__label">Open Risks</div>
                    <div class="kpi-card__sub">${s.risks.critical} critical</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${s.actions.open}</div>
                    <div class="kpi-card__label">Open Actions</div>
                    <div class="kpi-card__sub">${s.actions.overdue} overdue</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${s.issues.open}</div>
                    <div class="kpi-card__label">Open Issues</div>
                    <div class="kpi-card__sub">${s.issues.critical} critical</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${s.decisions.pending}</div>
                    <div class="kpi-card__label">Pending Decisions</div>
                    <div class="kpi-card__sub">${s.decisions.total} total</div>
                </div>
            `;
        } catch (e) {
            document.getElementById('raidStats').innerHTML =
                `<p class="text-muted">⚠️ Stats unavailable</p>`;
        }
    }

    // ── Heatmap ──────────────────────────────────────────────────────────
    async function loadHeatmap() {
        try {
            const h = await API.get(`/programs/${_programId}/raid/heatmap`);
            const ragColors = {green: '#28a745', amber: '#ffc107', orange: '#fd7e14', red: '#dc3545'};
            let html = '<table class="heatmap-table"><thead><tr><th></th>';
            h.labels.impact.forEach(l => { html += `<th>${l}</th>`; });
            html += '</tr></thead><tbody>';
            for (let p = 4; p >= 0; p--) {
                html += `<tr><th>${h.labels.probability[p]}</th>`;
                for (let i = 0; i < 5; i++) {
                    const cell = h.matrix[p][i];
                    const score = (p + 1) * (i + 1);
                    const bg = score <= 4 ? '#d4edda' : score <= 9 ? '#fff3cd' : score <= 15 ? '#ffe0b2' : '#f8d7da';
                    html += `<td style="background:${bg};text-align:center;min-width:60px;padding:4px;cursor:${cell.length ? 'pointer' : 'default'}"
                              title="Score: ${score}${cell.length ? ' — ' + cell.map(r => r.code).join(', ') : ''}"
                              ${cell.length ? `onclick="RaidView.showHeatmapCell(${JSON.stringify(cell).replace(/"/g, '&quot;')})"` : ''}>
                        ${cell.length ? `<strong>${cell.length}</strong>` : '-'}
                    </td>`;
                }
                html += '</tr>';
            }
            html += '</tbody></table>';
            document.getElementById('riskHeatmap').innerHTML = html;
        } catch (e) {
            document.getElementById('riskHeatmap').innerHTML =
                `<p class="text-muted">No heatmap data</p>`;
        }
    }

    function showHeatmapCell(risks) {
        const html = `<div class="modal">
            <div class="modal__header"><h3>Risks in Cell</h3>
                <button class="btn btn-sm" onclick="App.closeModal()">✕</button>
            </div>
            <div class="modal__body">
                <table class="table"><thead><tr><th>Code</th><th>Title</th><th>RAG</th></tr></thead>
                <tbody>${risks.map(r => `<tr><td>${r.code}</td><td>${r.title}</td>
                    <td><span class="badge badge-${r.rag_status}">${r.rag_status}</span></td></tr>`).join('')}
                </tbody></table>
            </div>
        </div>`;
        App.openModal(html);
    }

    // ── List Views ───────────────────────────────────────────────────────
    let _currentTab = 'risks';

    function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('.tabs .tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        loadList(tab);
    }

    async function loadList(tab) {
        const container = document.getElementById('raidListContainer');
        try {
            let items = [];
            if (tab === 'risks') items = await API.get(`/programs/${_programId}/risks`);
            else if (tab === 'actions') items = await API.get(`/programs/${_programId}/actions`);
            else if (tab === 'issues') items = await API.get(`/programs/${_programId}/issues`);
            else if (tab === 'decisions') items = await API.get(`/programs/${_programId}/decisions`);

            if (!items.length) {
                container.innerHTML = `<div class="empty-state"><p>No ${tab} found.</p></div>`;
                return;
            }

            container.innerHTML = renderTable(tab, items);
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
        }
    }

    function renderTable(tab, items) {
        const columns = {
            risks: ['code', 'title', 'status', 'priority', 'risk_score', 'rag_status', 'owner'],
            actions: ['code', 'title', 'status', 'priority', 'action_type', 'due_date', 'owner'],
            issues: ['code', 'title', 'status', 'severity', 'priority', 'owner'],
            decisions: ['code', 'title', 'status', 'priority', 'decision_owner', 'reversible'],
        };
        const cols = columns[tab] || ['code', 'title', 'status'];

        let html = '<table class="table table-hover"><thead><tr>';
        cols.forEach(c => { html += `<th>${c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</th>`; });
        html += '<th>Actions</th></tr></thead><tbody>';

        items.forEach(item => {
            html += `<tr style="cursor:pointer" onclick="RaidView.openDetail('${tab}', ${item.id})">`;
            cols.forEach(c => {
                let val = item[c];
                if (c === 'rag_status') {
                    const colors = {green: '🟢', amber: '🟡', orange: '🟠', red: '🔴'};
                    val = `${colors[val] || ''} ${val}`;
                } else if (c === 'status' || c === 'priority' || c === 'severity') {
                    val = `<span class="badge badge-${val}">${val}</span>`;
                } else if (c === 'risk_score') {
                    val = `<strong>${val}</strong>`;
                } else if (c === 'reversible') {
                    val = val ? '✅ Yes' : '❌ No';
                }
                html += `<td>${val ?? '-'}</td>`;
            });
            html += `<td>
                <button class="btn btn-sm" onclick="event.stopPropagation();RaidView.openEdit('${tab}', ${item.id})" title="Edit">✏️</button>
                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();RaidView.deleteItem('${tab}', ${item.id})" title="Delete">🗑️</button>
            </td></tr>`;
        });
        html += '</tbody></table>';
        return html;
    }

    // ── Detail Modal ─────────────────────────────────────────────────────
    async function openDetail(tab, id) {
        const singular = tab.slice(0, -1);  // risks → risk
        try {
            const item = await API.get(`/${tab}/${id}`);
            const fields = Object.entries(item)
                .filter(([k]) => !['id', 'raid_type', 'program_id'].includes(k))
                .map(([k, v]) => {
                    const label = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    return `<tr><td><strong>${label}</strong></td><td>${v ?? '-'}</td></tr>`;
                }).join('');

            App.openModal(`
                <div class="modal">
                    <div class="modal__header">
                        <h3>${item.code} — ${item.title}</h3>
                        <button class="btn btn-sm" onclick="App.closeModal()">✕</button>
                    </div>
                    <div class="modal__body">
                        <table class="table">${fields}</table>
                    </div>
                    <div class="modal__footer">
                        <button class="btn btn-primary" onclick="RaidView.openEdit('${tab}', ${id})">Edit</button>
                        <button class="btn" onclick="App.closeModal()">Close</button>
                    </div>
                </div>
            `);
        } catch (e) {
            App.toast(`Error loading ${singular}: ${e.message}`, 'error');
        }
    }

    // ── Create / Edit Forms ──────────────────────────────────────────────
    function openCreate(type) {
        const title = type.charAt(0).toUpperCase() + type.slice(1);
        App.openModal(`
            <div class="modal">
                <div class="modal__header"><h3>New ${title}</h3>
                    <button class="btn btn-sm" onclick="App.closeModal()">✕</button>
                </div>
                <div class="modal__body">
                    ${_getForm(type, {})}
                </div>
                <div class="modal__footer">
                    <button class="btn btn-primary" onclick="RaidView.submitCreate('${type}')">Create</button>
                    <button class="btn" onclick="App.closeModal()">Cancel</button>
                </div>
            </div>
        `);
    }

    async function openEdit(tab, id) {
        const singular = tab.slice(0, -1);
        try {
            const item = await API.get(`/${tab}/${id}`);
            App.openModal(`
                <div class="modal">
                    <div class="modal__header"><h3>Edit ${item.code}</h3>
                        <button class="btn btn-sm" onclick="App.closeModal()">✕</button>
                    </div>
                    <div class="modal__body">
                        ${_getForm(singular, item)}
                    </div>
                    <div class="modal__footer">
                        <button class="btn btn-primary" onclick="RaidView.submitEdit('${tab}', ${id})">Save</button>
                        <button class="btn" onclick="App.closeModal()">Cancel</button>
                    </div>
                </div>
            `);
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    function _getForm(type, data) {
        const v = (k) => data[k] || '';
        let common = `
            <div class="form-group"><label>Title *</label>
                <input id="rf_title" class="form-control" value="${v('title')}" required></div>
            <div class="form-group"><label>Description</label>
                <textarea id="rf_description" class="form-control" rows="3">${v('description')}</textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Owner</label>
                    <input id="rf_owner" class="form-control" value="${v('owner')}"></div>
                <div class="form-group"><label>Priority</label>
                    <select id="rf_priority" class="form-control">
                        ${['low', 'medium', 'high', 'critical'].map(p =>
                            `<option value="${p}" ${v('priority') === p ? 'selected' : ''}>${p}</option>`
                        ).join('')}
                    </select></div>
            </div>
        `;

        if (type === 'risk') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Probability (1-5)</label>
                        <input id="rf_probability" type="number" min="1" max="5" class="form-control" value="${data.probability || 3}"></div>
                    <div class="form-group"><label>Impact (1-5)</label>
                        <input id="rf_impact" type="number" min="1" max="5" class="form-control" value="${data.impact || 3}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Category</label>
                        <select id="rf_risk_category" class="form-control">
                            ${['technical', 'organisational', 'commercial', 'external', 'schedule', 'resource', 'scope'].map(c =>
                                `<option value="${c}" ${v('risk_category') === c ? 'selected' : ''}>${c}</option>`
                            ).join('')}
                        </select></div>
                    <div class="form-group"><label>Response</label>
                        <select id="rf_risk_response" class="form-control">
                            ${['avoid', 'transfer', 'mitigate', 'accept', 'escalate'].map(r =>
                                `<option value="${r}" ${v('risk_response') === r ? 'selected' : ''}>${r}</option>`
                            ).join('')}
                        </select></div>
                </div>
                <div class="form-group"><label>Mitigation Plan</label>
                    <textarea id="rf_mitigation_plan" class="form-control" rows="2">${v('mitigation_plan')}</textarea></div>
                <div class="form-group"><label>Contingency Plan</label>
                    <textarea id="rf_contingency_plan" class="form-control" rows="2">${v('contingency_plan')}</textarea></div>
            `;
        } else if (type === 'action') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Due Date</label>
                        <input id="rf_due_date" type="date" class="form-control" value="${v('due_date')}"></div>
                    <div class="form-group"><label>Type</label>
                        <select id="rf_action_type" class="form-control">
                            ${['preventive', 'corrective', 'detective', 'improvement', 'follow_up'].map(t =>
                                `<option value="${t}" ${v('action_type') === t ? 'selected' : ''}>${t}</option>`
                            ).join('')}
                        </select></div>
                </div>
            `;
        } else if (type === 'issue') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Severity</label>
                        <select id="rf_severity" class="form-control">
                            ${['minor', 'moderate', 'major', 'critical'].map(s =>
                                `<option value="${s}" ${v('severity') === s ? 'selected' : ''}>${s}</option>`
                            ).join('')}
                        </select></div>
                    <div class="form-group"><label>Escalation Path</label>
                        <input id="rf_escalation_path" class="form-control" value="${v('escalation_path')}"></div>
                </div>
                <div class="form-group"><label>Root Cause</label>
                    <textarea id="rf_root_cause" class="form-control" rows="2">${v('root_cause')}</textarea></div>
            `;
        } else if (type === 'decision') {
            common += `
                <div class="form-group"><label>Decision Owner</label>
                    <input id="rf_decision_owner" class="form-control" value="${v('decision_owner')}"></div>
                <div class="form-group"><label>Alternatives</label>
                    <textarea id="rf_alternatives" class="form-control" rows="2">${v('alternatives')}</textarea></div>
                <div class="form-group"><label>Rationale</label>
                    <textarea id="rf_rationale" class="form-control" rows="2">${v('rationale')}</textarea></div>
                <div class="form-group"><label>Reversible</label>
                    <select id="rf_reversible" class="form-control">
                        <option value="true" ${data.reversible !== false ? 'selected' : ''}>Yes</option>
                        <option value="false" ${data.reversible === false ? 'selected' : ''}>No</option>
                    </select></div>
            `;
        }
        return common;
    }

    function _collectFormData(type) {
        const data = {
            title: document.getElementById('rf_title')?.value || '',
            description: document.getElementById('rf_description')?.value || '',
            owner: document.getElementById('rf_owner')?.value || '',
            priority: document.getElementById('rf_priority')?.value || 'medium',
        };
        if (type === 'risk') {
            data.probability = parseInt(document.getElementById('rf_probability')?.value) || 3;
            data.impact = parseInt(document.getElementById('rf_impact')?.value) || 3;
            data.risk_category = document.getElementById('rf_risk_category')?.value || 'technical';
            data.risk_response = document.getElementById('rf_risk_response')?.value || 'mitigate';
            data.mitigation_plan = document.getElementById('rf_mitigation_plan')?.value || '';
            data.contingency_plan = document.getElementById('rf_contingency_plan')?.value || '';
        } else if (type === 'action') {
            data.due_date = document.getElementById('rf_due_date')?.value || null;
            data.action_type = document.getElementById('rf_action_type')?.value || 'corrective';
        } else if (type === 'issue') {
            data.severity = document.getElementById('rf_severity')?.value || 'moderate';
            data.escalation_path = document.getElementById('rf_escalation_path')?.value || '';
            data.root_cause = document.getElementById('rf_root_cause')?.value || '';
        } else if (type === 'decision') {
            data.decision_owner = document.getElementById('rf_decision_owner')?.value || '';
            data.alternatives = document.getElementById('rf_alternatives')?.value || '';
            data.rationale = document.getElementById('rf_rationale')?.value || '';
            data.reversible = document.getElementById('rf_reversible')?.value === 'true';
        }
        return data;
    }

    async function submitCreate(type) {
        const data = _collectFormData(type);
        if (!data.title) { App.toast('Title is required', 'error'); return; }
        try {
            await API.post(`/programs/${_programId}/${type}s`, data);
            App.closeModal();
            App.toast(`${type} created`, 'success');
            render();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function submitEdit(tab, id) {
        const singular = tab.slice(0, -1);
        const data = _collectFormData(singular);
        if (!data.title) { App.toast('Title is required', 'error'); return; }
        try {
            await API.put(`/${tab}/${id}`, data);
            App.closeModal();
            App.toast(`${singular} updated`, 'success');
            render();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function deleteItem(tab, id) {
        if (!confirm(`Delete this ${tab.slice(0, -1)}?`)) return;
        try {
            await API.delete(`/${tab}/${id}`);
            App.toast('Deleted', 'success');
            loadList(_currentTab);
            loadStats();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    // ── Public API ───────────────────────────────────────────────────────
    return {
        render, switchTab, openDetail, openCreate, openEdit,
        submitCreate, submitEdit, deleteItem, showHeatmapCell,
    };
})();
