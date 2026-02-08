/**
 * SAP Transformation Management Platform
 * Program View — Sprint 2: Full program management with tabbed sub-views.
 *
 * Tabs: Overview | Phases & Gates | Workstreams | Team | Committees
 */

const ProgramView = (() => {
    let programs = [];
    let currentProgram = null;
    let currentTab = 'overview';

    // ── Render program list ──────────────────────────────────────────────
    async function render() {
        currentProgram = null;
        currentTab = 'overview';
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <h1>Programs</h1>
                <button class="btn btn-primary" onclick="ProgramView.showCreateModal()">
                    + New Program
                </button>
            </div>
            <div class="card">
                <div id="programTableContainer">
                    <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
                </div>
            </div>
        `;
        await loadPrograms();
    }

    async function loadPrograms() {
        try {
            programs = await API.get('/programs');
            renderTable();
        } catch (err) {
            document.getElementById('programTableContainer').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
        }
    }

    function renderTable() {
        const container = document.getElementById('programTableContainer');
        if (programs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📋</div>
                    <div class="empty-state__title">No programs found</div>
                    <p>Create your first SAP transformation program.</p><br>
                    <button class="btn btn-primary" onclick="ProgramView.showCreateModal()">+ New Program</button>
                </div>`;
            return;
        }

        container.innerHTML = `
            <table class="data-table">
                <thead><tr>
                    <th>ID</th><th>Name</th><th>Type</th><th>Methodology</th>
                    <th>Status</th><th>Priority</th><th>SAP Product</th><th>Start Date</th><th>Actions</th>
                </tr></thead>
                <tbody>
                    ${programs.map(p => `
                        <tr>
                            <td>${p.id}</td>
                            <td><a href="#" onclick="ProgramView.openDetail(${p.id});return false"><strong>${escHtml(p.name)}</strong></a></td>
                            <td>${p.project_type}</td>
                            <td>${p.methodology}</td>
                            <td><span class="badge badge-${p.status}">${p.status}</span></td>
                            <td>${p.priority}</td>
                            <td>${p.sap_product}</td>
                            <td>${p.start_date || '—'}</td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="ProgramView.openDetail(${p.id})">View</button>
                                <button class="btn btn-danger btn-sm" onclick="ProgramView.deleteProgram(${p.id})">Delete</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    }

    // ═════════════════════════════════════════════════════════════════════
    // DETAIL VIEW (tabbed)
    // ═════════════════════════════════════════════════════════════════════

    async function openDetail(id) {
        try {
            currentProgram = await API.get(`/programs/${id}`);
        } catch (err) {
            App.toast(err.message, 'error');
            return;
        }
        renderDetail();
    }

    function renderDetail() {
        const p = currentProgram;
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="ProgramView.render()" style="margin-right:12px">← Back</button>
                    <span style="font-size:1.5rem;font-weight:700">${escHtml(p.name)}</span>
                    <span class="badge badge-${p.status}" style="margin-left:8px">${p.status}</span>
                </div>
                <button class="btn btn-primary" onclick="ProgramView.showEditModal(${p.id})">Edit Program</button>
            </div>

            <div class="tabs" id="programTabs">
                <button class="tab-btn ${currentTab === 'overview' ? 'active' : ''}" data-tab="overview">Overview</button>
                <button class="tab-btn ${currentTab === 'phases' ? 'active' : ''}" data-tab="phases">Phases & Gates</button>
                <button class="tab-btn ${currentTab === 'workstreams' ? 'active' : ''}" data-tab="workstreams">Workstreams</button>
                <button class="tab-btn ${currentTab === 'team' ? 'active' : ''}" data-tab="team">Team</button>
                <button class="tab-btn ${currentTab === 'committees' ? 'active' : ''}" data-tab="committees">Committees</button>
            </div>
            <div id="tabContent" class="card" style="margin-top:0;border-top-left-radius:0;border-top-right-radius:0"></div>
        `;

        // Tab click handlers
        document.querySelectorAll('#programTabs .tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentTab = btn.dataset.tab;
                document.querySelectorAll('#programTabs .tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderTab();
            });
        });

        renderTab();
    }

    function renderTab() {
        const container = document.getElementById('tabContent');
        switch (currentTab) {
            case 'overview':    renderOverviewTab(container); break;
            case 'phases':      renderPhasesTab(container); break;
            case 'workstreams': renderWorkstreamsTab(container); break;
            case 'team':        renderTeamTab(container); break;
            case 'committees':  renderCommitteesTab(container); break;
        }
    }

    // ── Overview Tab ─────────────────────────────────────────────────────
    function renderOverviewTab(container) {
        const p = currentProgram;
        container.innerHTML = `
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-card__value">${(p.phases || []).length}</div>
                    <div class="kpi-card__label">Phases</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${(p.workstreams || []).length}</div>
                    <div class="kpi-card__label">Workstreams</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${(p.team_members || []).filter(m => m.is_active).length}</div>
                    <div class="kpi-card__label">Team Members</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${(p.committees || []).length}</div>
                    <div class="kpi-card__label">Committees</div>
                </div>
            </div>
            <div class="detail-grid">
                <div class="detail-section">
                    <h3>Program Details</h3>
                    <dl class="detail-list">
                        <dt>Description</dt><dd>${escHtml(p.description || '—')}</dd>
                        <dt>Project Type</dt><dd>${p.project_type}</dd>
                        <dt>Methodology</dt><dd>${p.methodology}</dd>
                        <dt>SAP Product</dt><dd>${p.sap_product}</dd>
                        <dt>Deployment</dt><dd>${p.deployment_option}</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Timeline</h3>
                    <dl class="detail-list">
                        <dt>Priority</dt><dd><span class="badge badge-${p.priority}">${p.priority}</span></dd>
                        <dt>Start Date</dt><dd>${p.start_date || '—'}</dd>
                        <dt>End Date</dt><dd>${p.end_date || '—'}</dd>
                        <dt>Go-Live Date</dt><dd>${p.go_live_date || '—'}</dd>
                        <dt>Created</dt><dd>${p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}</dd>
                    </dl>
                </div>
            </div>
        `;
    }

    // ── Phases Tab ───────────────────────────────────────────────────────
    function renderPhasesTab(container) {
        const phases = currentProgram.phases || [];
        container.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                <h3>Phases & Gates</h3>
                <button class="btn btn-primary btn-sm" onclick="ProgramView.showPhaseModal()">+ Add Phase</button>
            </div>
            ${phases.length === 0
                ? '<div class="empty-state"><div class="empty-state__icon">📅</div><div class="empty-state__title">No phases yet</div></div>'
                : phases.map(ph => `
                    <div class="phase-card">
                        <div class="phase-header">
                            <div>
                                <strong>${ph.order}. ${escHtml(ph.name)}</strong>
                                <span class="badge badge-${ph.status}">${ph.status}</span>
                            </div>
                            <div>
                                <span class="completion-bar" title="${ph.completion_pct}% complete">
                                    <span class="completion-fill" style="width:${ph.completion_pct}%"></span>
                                </span>
                                <button class="btn btn-secondary btn-sm" onclick="ProgramView.showPhaseModal(${ph.id})">Edit</button>
                                <button class="btn btn-danger btn-sm" onclick="ProgramView.deletePhase(${ph.id})">×</button>
                            </div>
                        </div>
                        <div class="phase-body">
                            <p style="color:var(--text-secondary);font-size:0.85rem">${escHtml(ph.description || '')}</p>
                            <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:4px">
                                Plan: ${ph.planned_start || '?'} → ${ph.planned_end || '?'}
                                ${ph.actual_start ? ` | Actual: ${ph.actual_start} → ${ph.actual_end || '...'}` : ''}
                            </div>
                        </div>
                        <div class="gates-section">
                            <div style="display:flex;justify-content:space-between;align-items:center">
                                <strong style="font-size:0.85rem">Gates</strong>
                                <button class="btn btn-secondary btn-sm" onclick="ProgramView.showGateModal(${ph.id})">+ Gate</button>
                            </div>
                            ${(ph.gates || []).length === 0
                                ? '<div style="color:var(--text-secondary);font-size:0.8rem;padding:8px 0">No gates</div>'
                                : `<table class="data-table" style="margin-top:8px">
                                    <thead><tr><th>Gate</th><th>Type</th><th>Status</th><th>Planned</th><th>Actions</th></tr></thead>
                                    <tbody>
                                        ${(ph.gates || []).map(g => `
                                            <tr>
                                                <td>${escHtml(g.name)}</td>
                                                <td>${g.gate_type}</td>
                                                <td><span class="badge badge-${g.status}">${g.status}</span></td>
                                                <td>${g.planned_date || '—'}</td>
                                                <td>
                                                    <button class="btn btn-secondary btn-sm" onclick="ProgramView.showGateModal(${ph.id}, ${g.id})">Edit</button>
                                                    <button class="btn btn-danger btn-sm" onclick="ProgramView.deleteGate(${g.id})">×</button>
                                                </td>
                                            </tr>`).join('')}
                                    </tbody>
                                </table>`
                            }
                        </div>
                    </div>
                `).join('')
            }
        `;
    }

    // ── Workstreams Tab ──────────────────────────────────────────────────
    function renderWorkstreamsTab(container) {
        const ws = currentProgram.workstreams || [];
        container.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                <h3>Workstreams</h3>
                <button class="btn btn-primary btn-sm" onclick="ProgramView.showWorkstreamModal()">+ Add Workstream</button>
            </div>
            ${ws.length === 0
                ? '<div class="empty-state"><div class="empty-state__icon">🔧</div><div class="empty-state__title">No workstreams yet</div></div>'
                : `<table class="data-table">
                    <thead><tr><th>Name</th><th>Type</th><th>Lead</th><th>Status</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${ws.map(w => `
                            <tr>
                                <td><strong>${escHtml(w.name)}</strong><br><small style="color:var(--text-secondary)">${escHtml(w.description || '')}</small></td>
                                <td>${w.ws_type}</td>
                                <td>${escHtml(w.lead_name || '—')}</td>
                                <td><span class="badge badge-${w.status}">${w.status}</span></td>
                                <td>
                                    <button class="btn btn-secondary btn-sm" onclick="ProgramView.showWorkstreamModal(${w.id})">Edit</button>
                                    <button class="btn btn-danger btn-sm" onclick="ProgramView.deleteWorkstream(${w.id})">Delete</button>
                                </td>
                            </tr>`).join('')}
                    </tbody>
                </table>`
            }
        `;
    }

    // ── Team Tab ─────────────────────────────────────────────────────────
    function renderTeamTab(container) {
        const members = currentProgram.team_members || [];
        container.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                <h3>Team Members</h3>
                <button class="btn btn-primary btn-sm" onclick="ProgramView.showTeamModal()">+ Add Member</button>
            </div>
            ${members.length === 0
                ? '<div class="empty-state"><div class="empty-state__icon">👥</div><div class="empty-state__title">No team members yet</div></div>'
                : `<table class="data-table">
                    <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>RACI</th><th>Organization</th><th>Active</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${members.map(m => `
                            <tr>
                                <td><strong>${escHtml(m.name)}</strong></td>
                                <td>${escHtml(m.email || '—')}</td>
                                <td>${m.role}</td>
                                <td><span class="badge badge-${m.raci}">${m.raci}</span></td>
                                <td>${escHtml(m.organization || '—')}</td>
                                <td>${m.is_active ? '✅' : '❌'}</td>
                                <td>
                                    <button class="btn btn-secondary btn-sm" onclick="ProgramView.showTeamModal(${m.id})">Edit</button>
                                    <button class="btn btn-danger btn-sm" onclick="ProgramView.deleteTeamMember(${m.id})">Remove</button>
                                </td>
                            </tr>`).join('')}
                    </tbody>
                </table>`
            }
        `;
    }

    // ── Committees Tab ───────────────────────────────────────────────────
    function renderCommitteesTab(container) {
        const comms = currentProgram.committees || [];
        container.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                <h3>Committees</h3>
                <button class="btn btn-primary btn-sm" onclick="ProgramView.showCommitteeModal()">+ Add Committee</button>
            </div>
            ${comms.length === 0
                ? '<div class="empty-state"><div class="empty-state__icon">🏛️</div><div class="empty-state__title">No committees yet</div></div>'
                : `<table class="data-table">
                    <thead><tr><th>Name</th><th>Type</th><th>Frequency</th><th>Chair</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${comms.map(c => `
                            <tr>
                                <td><strong>${escHtml(c.name)}</strong><br><small style="color:var(--text-secondary)">${escHtml(c.description || '')}</small></td>
                                <td>${c.committee_type}</td>
                                <td>${c.meeting_frequency}</td>
                                <td>${escHtml(c.chair_name || '—')}</td>
                                <td>
                                    <button class="btn btn-secondary btn-sm" onclick="ProgramView.showCommitteeModal(${c.id})">Edit</button>
                                    <button class="btn btn-danger btn-sm" onclick="ProgramView.deleteCommittee(${c.id})">Delete</button>
                                </td>
                            </tr>`).join('')}
                    </tbody>
                </table>`
            }
        `;
    }


    // ═════════════════════════════════════════════════════════════════════
    // MODALS
    // ═════════════════════════════════════════════════════════════════════

    // ── Program Modal ────────────────────────────────────────────────────
    function showCreateModal() {
        App.openModal(programFormHtml('Create Program', {}));
    }

    function showEditModal(id) {
        const p = currentProgram || programs.find(x => x.id === id);
        if (!p) return;
        App.openModal(programFormHtml('Edit Program', p));
    }

    function programFormHtml(title, p) {
        const isEdit = !!p.id;
        return `
            <div class="modal-header">
                <h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form id="programForm" onsubmit="ProgramView.handleSubmit(event, ${p.id || 'null'})">
                <div class="form-group">
                    <label>Program Name *</label>
                    <input name="name" required value="${escAttr(p.name || '')}" placeholder="e.g. ACME S/4HANA Greenfield">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="3" placeholder="Brief description...">${escHtml(p.description || '')}</textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Project Type</label>
                        <select name="project_type">
                            ${selectOpts(['greenfield','brownfield','bluefield','selective_data_transition'], p.project_type)}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Methodology</label>
                        <select name="methodology">
                            ${selectOpts(['sap_activate','agile','waterfall','hybrid'], p.methodology)}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Status</label>
                        <select name="status">
                            ${selectOpts(['planning','active','on_hold','completed','cancelled'], p.status)}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Priority</label>
                        <select name="priority">
                            ${selectOpts(['low','medium','high','critical'], p.priority)}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>SAP Product</label>
                        <select name="sap_product">
                            ${selectOpts(['S/4HANA','SuccessFactors','Ariba','BTP','Other'], p.sap_product)}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Deployment</label>
                        <select name="deployment_option">
                            ${selectOpts(['on_premise','cloud','hybrid'], p.deployment_option)}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Start Date</label><input name="start_date" type="date" value="${p.start_date || ''}"></div>
                    <div class="form-group"><label>End Date</label><input name="end_date" type="date" value="${p.end_date || ''}"></div>
                </div>
                <div class="form-group"><label>Go-Live Date</label><input name="go_live_date" type="date" value="${p.go_live_date || ''}"></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'}</button>
                </div>
            </form>`;
    }

    async function handleSubmit(event, id) {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(event.target).entries());
        try {
            if (id) {
                await API.put(`/programs/${id}`, data);
                App.toast('Program updated', 'success');
            } else {
                await API.post('/programs', data);
                App.toast('Program created', 'success');
            }
            App.closeModal();
            if (currentProgram && id) {
                await openDetail(id);
            } else {
                await loadPrograms();
            }
            App.updateProjectSelector();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteProgram(id) {
        const p = programs.find(x => x.id === id);
        if (!confirm(`Delete program "${p?.name}"?`)) return;
        try {
            await API.delete(`/programs/${id}`);
            App.toast('Program deleted', 'success');
            await loadPrograms();
            App.updateProjectSelector();
        } catch (err) { App.toast(err.message, 'error'); }
    }


    // ── Phase Modal ──────────────────────────────────────────────────────
    function showPhaseModal(phaseId) {
        const phases = currentProgram.phases || [];
        const ph = phaseId ? phases.find(x => x.id === phaseId) : {};
        const isEdit = !!ph.id;
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? 'Edit Phase' : 'Add Phase'}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form onsubmit="ProgramView.handlePhaseSubmit(event, ${ph.id || 'null'})">
                <div class="form-group"><label>Phase Name *</label><input name="name" required value="${escAttr(ph.name || '')}"></div>
                <div class="form-group"><label>Description</label><textarea name="description" rows="2">${escHtml(ph.description || '')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Order</label><input name="order" type="number" value="${ph.order ?? phases.length + 1}"></div>
                    <div class="form-group"><label>Status</label><select name="status">${selectOpts(['not_started','in_progress','completed','skipped'], ph.status)}</select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Planned Start</label><input name="planned_start" type="date" value="${ph.planned_start || ''}"></div>
                    <div class="form-group"><label>Planned End</label><input name="planned_end" type="date" value="${ph.planned_end || ''}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Actual Start</label><input name="actual_start" type="date" value="${ph.actual_start || ''}"></div>
                    <div class="form-group"><label>Actual End</label><input name="actual_end" type="date" value="${ph.actual_end || ''}"></div>
                </div>
                <div class="form-group"><label>Completion %</label><input name="completion_pct" type="number" min="0" max="100" value="${ph.completion_pct ?? 0}"></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'}</button>
                </div>
            </form>`);
    }

    async function handlePhaseSubmit(event, phaseId) {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(event.target).entries());
        data.order = parseInt(data.order) || 0;
        data.completion_pct = parseInt(data.completion_pct) || 0;
        try {
            if (phaseId) {
                await API.put(`/phases/${phaseId}`, data);
                App.toast('Phase updated', 'success');
            } else {
                await API.post(`/programs/${currentProgram.id}/phases`, data);
                App.toast('Phase created', 'success');
            }
            App.closeModal();
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deletePhase(id) {
        if (!confirm('Delete this phase and its gates?')) return;
        try {
            await API.delete(`/phases/${id}`);
            App.toast('Phase deleted', 'success');
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }


    // ── Gate Modal ───────────────────────────────────────────────────────
    function showGateModal(phaseId, gateId) {
        const phases = currentProgram.phases || [];
        const phase = phases.find(x => x.id === phaseId);
        const g = gateId ? (phase.gates || []).find(x => x.id === gateId) : {};
        const isEdit = !!g.id;
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? 'Edit Gate' : 'Add Gate'}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form onsubmit="ProgramView.handleGateSubmit(event, ${phaseId}, ${g.id || 'null'})">
                <div class="form-group"><label>Gate Name *</label><input name="name" required value="${escAttr(g.name || '')}"></div>
                <div class="form-group"><label>Description</label><textarea name="description" rows="2">${escHtml(g.description || '')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label><select name="gate_type">${selectOpts(['quality_gate','milestone','decision_point'], g.gate_type)}</select></div>
                    <div class="form-group"><label>Status</label><select name="status">${selectOpts(['pending','passed','failed','waived'], g.status)}</select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Planned Date</label><input name="planned_date" type="date" value="${g.planned_date || ''}"></div>
                    <div class="form-group"><label>Actual Date</label><input name="actual_date" type="date" value="${g.actual_date || ''}"></div>
                </div>
                <div class="form-group"><label>Criteria</label><textarea name="criteria" rows="3" placeholder="Acceptance criteria...">${escHtml(g.criteria || '')}</textarea></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'}</button>
                </div>
            </form>`);
    }

    async function handleGateSubmit(event, phaseId, gateId) {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(event.target).entries());
        try {
            if (gateId) {
                await API.put(`/gates/${gateId}`, data);
                App.toast('Gate updated', 'success');
            } else {
                await API.post(`/phases/${phaseId}/gates`, data);
                App.toast('Gate created', 'success');
            }
            App.closeModal();
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteGate(id) {
        if (!confirm('Delete this gate?')) return;
        try {
            await API.delete(`/gates/${id}`);
            App.toast('Gate deleted', 'success');
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }


    // ── Workstream Modal ─────────────────────────────────────────────────
    function showWorkstreamModal(wsId) {
        const wsList = currentProgram.workstreams || [];
        const w = wsId ? wsList.find(x => x.id === wsId) : {};
        const isEdit = !!w.id;
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? 'Edit Workstream' : 'Add Workstream'}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form onsubmit="ProgramView.handleWorkstreamSubmit(event, ${w.id || 'null'})">
                <div class="form-group"><label>Workstream Name *</label><input name="name" required value="${escAttr(w.name || '')}" placeholder="e.g. FI/CO, MM/PP, Basis"></div>
                <div class="form-group"><label>Description</label><textarea name="description" rows="2">${escHtml(w.description || '')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label><select name="ws_type">${selectOpts(['functional','technical','cross_cutting'], w.ws_type)}</select></div>
                    <div class="form-group"><label>Status</label><select name="status">${selectOpts(['active','on_hold','completed'], w.status)}</select></div>
                </div>
                <div class="form-group"><label>Lead Name</label><input name="lead_name" value="${escAttr(w.lead_name || '')}"></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'}</button>
                </div>
            </form>`);
    }

    async function handleWorkstreamSubmit(event, id) {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(event.target).entries());
        try {
            if (id) {
                await API.put(`/workstreams/${id}`, data);
                App.toast('Workstream updated', 'success');
            } else {
                await API.post(`/programs/${currentProgram.id}/workstreams`, data);
                App.toast('Workstream created', 'success');
            }
            App.closeModal();
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteWorkstream(id) {
        if (!confirm('Delete this workstream?')) return;
        try {
            await API.delete(`/workstreams/${id}`);
            App.toast('Workstream deleted', 'success');
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }


    // ── Team Modal ───────────────────────────────────────────────────────
    function showTeamModal(memberId) {
        const members = currentProgram.team_members || [];
        const m = memberId ? members.find(x => x.id === memberId) : {};
        const isEdit = !!m.id;
        const wsList = currentProgram.workstreams || [];
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? 'Edit Team Member' : 'Add Team Member'}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form onsubmit="ProgramView.handleTeamSubmit(event, ${m.id || 'null'})">
                <div class="form-row">
                    <div class="form-group"><label>Name *</label><input name="name" required value="${escAttr(m.name || '')}"></div>
                    <div class="form-group"><label>Email</label><input name="email" type="email" value="${escAttr(m.email || '')}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Role</label><select name="role">${selectOpts(['program_manager','project_lead','stream_lead','consultant','developer','team_member'], m.role)}</select></div>
                    <div class="form-group"><label>RACI</label><select name="raci">${selectOpts(['responsible','accountable','consulted','informed'], m.raci)}</select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Organization</label><input name="organization" value="${escAttr(m.organization || '')}"></div>
                    <div class="form-group">
                        <label>Workstream</label>
                        <select name="workstream_id">
                            <option value="">— None —</option>
                            ${wsList.map(w => `<option value="${w.id}" ${w.id === m.workstream_id ? 'selected' : ''}>${escHtml(w.name)}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label><input type="checkbox" name="is_active" value="true" ${m.is_active !== false ? 'checked' : ''}> Active</label>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Add'}</button>
                </div>
            </form>`);
    }

    async function handleTeamSubmit(event, id) {
        event.preventDefault();
        const fd = new FormData(event.target);
        const data = Object.fromEntries(fd.entries());
        data.is_active = fd.has('is_active');
        data.workstream_id = data.workstream_id ? parseInt(data.workstream_id) : null;
        try {
            if (id) {
                await API.put(`/team/${id}`, data);
                App.toast('Team member updated', 'success');
            } else {
                await API.post(`/programs/${currentProgram.id}/team`, data);
                App.toast('Team member added', 'success');
            }
            App.closeModal();
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteTeamMember(id) {
        if (!confirm('Remove this team member?')) return;
        try {
            await API.delete(`/team/${id}`);
            App.toast('Team member removed', 'success');
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }


    // ── Committee Modal ──────────────────────────────────────────────────
    function showCommitteeModal(commId) {
        const comms = currentProgram.committees || [];
        const c = commId ? comms.find(x => x.id === commId) : {};
        const isEdit = !!c.id;
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? 'Edit Committee' : 'Add Committee'}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form onsubmit="ProgramView.handleCommitteeSubmit(event, ${c.id || 'null'})">
                <div class="form-group"><label>Committee Name *</label><input name="name" required value="${escAttr(c.name || '')}"></div>
                <div class="form-group"><label>Description</label><textarea name="description" rows="2">${escHtml(c.description || '')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label><select name="committee_type">${selectOpts(['steering','advisory','review','working_group'], c.committee_type)}</select></div>
                    <div class="form-group"><label>Frequency</label><select name="meeting_frequency">${selectOpts(['daily','weekly','biweekly','monthly','ad_hoc'], c.meeting_frequency)}</select></div>
                </div>
                <div class="form-group"><label>Chair</label><input name="chair_name" value="${escAttr(c.chair_name || '')}"></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'}</button>
                </div>
            </form>`);
    }

    async function handleCommitteeSubmit(event, id) {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(event.target).entries());
        try {
            if (id) {
                await API.put(`/committees/${id}`, data);
                App.toast('Committee updated', 'success');
            } else {
                await API.post(`/programs/${currentProgram.id}/committees`, data);
                App.toast('Committee created', 'success');
            }
            App.closeModal();
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteCommittee(id) {
        if (!confirm('Delete this committee?')) return;
        try {
            await API.delete(`/committees/${id}`);
            App.toast('Committee deleted', 'success');
            await openDetail(currentProgram.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }


    // ═════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ═════════════════════════════════════════════════════════════════════

    function escHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }
    function escAttr(s) { return (s || '').replace(/"/g, '&quot;'); }
    function selectOpts(options, selected) {
        return options.map(o =>
            `<option value="${o}" ${o === selected ? 'selected' : ''}>${o}</option>`
        ).join('');
    }

    // ── Public API ───────────────────────────────────────────────────────
    return {
        render, openDetail,
        showCreateModal, showEditModal, handleSubmit, deleteProgram,
        showPhaseModal, handlePhaseSubmit, deletePhase,
        showGateModal, handleGateSubmit, deleteGate,
        showWorkstreamModal, handleWorkstreamSubmit, deleteWorkstream,
        showTeamModal, handleTeamSubmit, deleteTeamMember,
        showCommitteeModal, handleCommitteeSubmit, deleteCommittee,
    };
})();
