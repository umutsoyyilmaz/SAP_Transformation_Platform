/**
 * SAP Transformation Management Platform
 * Scenario & Workshop View — Business scenarios with workshop drill-down.
 */

const ScenarioView = (() => {
    let scenarios = [];
    let currentScenario = null;
    let currentWorkshop = null;
    let programId = null;

    // ── Constants ────────────────────────────────────────────────────────
    const SESSION_TYPES = {
        fit_gap_workshop: { label: 'Fit-Gap Workshop', icon: '🔍', color: '#0070f2' },
        requirement_gathering: { label: 'Requirement Gathering', icon: '📋', color: '#107e3e' },
        process_mapping: { label: 'Process Mapping', icon: '🗺️', color: '#e76500' },
        review: { label: 'Review', icon: '👁️', color: '#5b738b' },
        design_workshop: { label: 'Design Workshop', icon: '✏️', color: '#8b47d7' },
        demo: { label: 'Demo', icon: '🖥️', color: '#188918' },
        sign_off: { label: 'Sign-Off', icon: '✅', color: '#0e6027' },
        training: { label: 'Training', icon: '🎓', color: '#c35500' },
    };

    const PROCESS_AREAS = {
        order_to_cash: 'Order to Cash (O2C)',
        procure_to_pay: 'Procure to Pay (P2P)',
        record_to_report: 'Record to Report (R2R)',
        plan_to_produce: 'Plan to Produce',
        hire_to_retire: 'Hire to Retire (H2R)',
        warehouse_mgmt: 'Warehouse Management',
        project_mgmt: 'Project Management',
        plant_maintenance: 'Plant Maintenance',
        quality_mgmt: 'Quality Management',
        other: 'Other',
    };

    // ── Render scenario list ─────────────────────────────────────────────
    async function render() {
        currentScenario = null;
        currentWorkshop = null;
        const prog = App.getActiveProgram();
        programId = prog ? prog.id : null;
        const main = document.getElementById('mainContent');

        if (!programId) {
            main.innerHTML = `
                <div class="page-header"><h1>Business Scenarios</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">🎯</div>
                    <div class="empty-state__title">Select a Program</div>
                    <p>Go to <a href="#" onclick="App.navigate('programs');return false">Programs</a> to select one.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>Business Scenarios</h1>
                <button class="btn btn-primary" onclick="ScenarioView.showCreateModal()">+ New Scenario</button>
            </div>
            <div id="scenarioFilters" class="filter-bar" style="margin-bottom:16px">
                <select id="filterStatus" class="form-input form-input--sm" onchange="ScenarioView.loadScenarios()">
                    <option value="">All Statuses</option>
                    <option value="draft">Draft</option>
                    <option value="in_analysis">In Analysis</option>
                    <option value="analyzed">Analyzed</option>
                    <option value="approved">Approved</option>
                    <option value="on_hold">On Hold</option>
                </select>
                <select id="filterPriority" class="form-input form-input--sm" onchange="ScenarioView.loadScenarios()">
                    <option value="">All Priorities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
            </div>
            <div id="scenarioListContainer">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>`;
        await loadScenarios();
    }

    async function loadScenarios() {
        try {
            let url = `/programs/${programId}/scenarios`;
            const params = [];
            const status = document.getElementById('filterStatus')?.value;
            const priority = document.getElementById('filterPriority')?.value;
            if (status) params.push(`status=${status}`);
            if (priority) params.push(`priority=${priority}`);
            if (params.length) url += '?' + params.join('&');

            scenarios = await API.get(url);
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
                    <p>Create your first business scenario to start workshop planning.</p><br>
                    <button class="btn btn-primary" onclick="ScenarioView.showCreateModal()">+ New Scenario</button>
                </div>`;
            return;
        }

        c.innerHTML = `
            <div class="scenario-grid">
                ${scenarios.map(s => {
                    const area = PROCESS_AREAS[s.process_area] || s.process_area;
                    return `
                    <div class="scenario-card" onclick="ScenarioView.openDetail(${s.id})" style="cursor:pointer">
                        <div class="scenario-card__header">
                            <h3>${escHtml(s.name)}</h3>
                            <div>
                                ${s.sap_module ? `<span class="badge badge-info">${escHtml(s.sap_module)}</span>` : ''}
                                <span class="badge badge-${s.status}">${formatStatus(s.status)}</span>
                                <span class="badge badge-priority-${s.priority}">${s.priority}</span>
                            </div>
                        </div>
                        <p class="scenario-card__desc">${escHtml(s.description || '—')}</p>
                        <div class="scenario-card__meta">
                            <div class="scenario-meta-item">
                                <span class="meta-label">Process Area</span>
                                <span>${area}</span>
                            </div>
                            <div class="scenario-meta-item">
                                <span class="meta-label">Owner</span>
                                <span>${escHtml(s.owner || '—')}</span>
                            </div>
                            <div class="scenario-meta-item">
                                <span class="meta-label">Workshops</span>
                                <span class="badge">${s.total_workshops || 0}</span>
                            </div>
                            <div class="scenario-meta-item">
                                <span class="meta-label">Requirements</span>
                                <span class="badge">${s.total_requirements || 0}</span>
                            </div>
                        </div>
                        <div class="scenario-card__actions" onclick="event.stopPropagation()">
                            <button class="btn btn-secondary btn-sm" onclick="ScenarioView.openDetail(${s.id})">View</button>
                            <button class="btn btn-danger btn-sm" onclick="ScenarioView.deleteScenario(${s.id})">Delete</button>
                        </div>
                    </div>`;
                }).join('')}
            </div>`;
    }

    // ── Scenario Detail view (with workshops) ────────────────────────────
    async function openDetail(id) {
        try {
            currentScenario = await API.get(`/scenarios/${id}`);
        } catch (err) { App.toast(err.message, 'error'); return; }
        renderDetail();
    }

    function renderDetail() {
        const s = currentScenario;
        const area = PROCESS_AREAS[s.process_area] || s.process_area;
        const workshops = s.workshops || [];
        const main = document.getElementById('mainContent');

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="ScenarioView.render()">← Back</button>
                    <h1 style="display:inline;margin-left:12px">${escHtml(s.name)}</h1>
                    ${s.sap_module ? `<span class="badge badge-info" style="margin-left:8px">${escHtml(s.sap_module)}</span>` : ''}
                    <span class="badge badge-${s.status}" style="margin-left:4px">${formatStatus(s.status)}</span>
                    <span class="badge badge-priority-${s.priority}" style="margin-left:4px">${s.priority}</span>
                </div>
                <button class="btn btn-primary" onclick="ScenarioView.showEditModal()">Edit Scenario</button>
            </div>

            <div class="detail-grid">
                <div class="detail-section">
                    <h3>Details</h3>
                    <dl class="detail-list">
                        <dt>Process Area</dt><dd>${area}</dd>
                        <dt>Owner</dt><dd>${escHtml(s.owner || '—')}</dd>
                        <dt>Workstream</dt><dd>${escHtml(s.workstream || '—')}</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Summary</h3>
                    <dl class="detail-list">
                        <dt>Workshops</dt><dd>${workshops.length}</dd>
                        <dt>Requirements</dt><dd>${s.total_requirements || 0}</dd>
                    </dl>
                </div>
            </div>

            ${s.description ? `<div class="card" style="margin-top:20px"><h3>Description</h3><p>${escHtml(s.description)}</p></div>` : ''}
            ${s.notes ? `<div class="card" style="margin-top:12px"><h3>Notes</h3><p>${escHtml(s.notes)}</p></div>` : ''}

            <div class="card" style="margin-top:20px">
                <div class="card-header">
                    <h3>Workshops / Sessions</h3>
                    <button class="btn btn-primary btn-sm" onclick="ScenarioView.showCreateWorkshopModal()">+ New Workshop</button>
                </div>
                <div id="workshopList"></div>
            </div>`;

        renderWorkshopList(workshops);
    }

    function renderWorkshopList(workshops) {
        const c = document.getElementById('workshopList');
        if (!workshops || workshops.length === 0) {
            c.innerHTML = '<p style="color:var(--sap-text-secondary);padding:16px">No workshops yet. Create one to start gathering requirements.</p>';
            return;
        }

        c.innerHTML = `
            <div class="workshop-grid">
                ${workshops.map(w => {
                    const typeInfo = SESSION_TYPES[w.session_type] || { label: w.session_type, icon: '📄', color: '#5b738b' };
                    const dateStr = w.session_date ? new Date(w.session_date).toLocaleDateString('tr-TR') : '—';
                    return `
                    <div class="workshop-card" onclick="ScenarioView.openWorkshop(${w.id})" style="cursor:pointer">
                        <div class="workshop-card__type" style="background:${typeInfo.color}">
                            <span>${typeInfo.icon}</span>
                        </div>
                        <div class="workshop-card__body">
                            <h4>${escHtml(w.title)}</h4>
                            <span class="badge badge-ws-type" style="background:${typeInfo.color}22;color:${typeInfo.color}">${typeInfo.label}</span>
                            <span class="badge badge-${w.status}">${formatStatus(w.status)}</span>
                            <div class="workshop-card__meta">
                                <span>📅 ${dateStr}</span>
                                ${w.facilitator ? `<span>👤 ${escHtml(w.facilitator)}</span>` : ''}
                                ${w.location ? `<span>📍 ${escHtml(w.location)}</span>` : ''}
                            </div>
                            ${w.fit_count || w.gap_count || w.partial_fit_count ? `
                            <div class="workshop-card__counts">
                                <span class="count-fit">✓ Fit: ${w.fit_count}</span>
                                <span class="count-gap">✗ Gap: ${w.gap_count}</span>
                                <span class="count-partial">◐ Partial: ${w.partial_fit_count}</span>
                            </div>` : ''}
                        </div>
                        <div class="workshop-card__actions" onclick="event.stopPropagation()">
                            <button class="btn btn-danger btn-sm" onclick="ScenarioView.deleteWorkshop(${w.id})">Delete</button>
                        </div>
                    </div>`;
                }).join('')}
            </div>`;
    }

    // ── Workshop Detail view ─────────────────────────────────────────────
    async function openWorkshop(id) {
        try {
            currentWorkshop = await API.get(`/workshops/${id}`);
        } catch (err) { App.toast(err.message, 'error'); return; }
        renderWorkshopDetail();
    }

    function renderWorkshopDetail() {
        const w = currentWorkshop;
        const typeInfo = SESSION_TYPES[w.session_type] || { label: w.session_type, icon: '📄', color: '#5b738b' };
        const dateStr = w.session_date ? new Date(w.session_date).toLocaleDateString('tr-TR') : '—';
        const requirements = w.requirements || [];
        const main = document.getElementById('mainContent');

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary btn-sm" onclick="ScenarioView.openDetail(${w.scenario_id})">← Back to Scenario</button>
                    <h1 style="display:inline;margin-left:12px">${escHtml(w.title)}</h1>
                    <span class="badge badge-ws-type" style="margin-left:8px;background:${typeInfo.color}22;color:${typeInfo.color}">${typeInfo.label}</span>
                    <span class="badge badge-${w.status}" style="margin-left:4px">${formatStatus(w.status)}</span>
                </div>
                <button class="btn btn-primary" onclick="ScenarioView.showEditWorkshopModal()">Edit Workshop</button>
            </div>

            <div class="detail-grid">
                <div class="detail-section">
                    <h3>Session Info</h3>
                    <dl class="detail-list">
                        <dt>Date</dt><dd>${dateStr}</dd>
                        <dt>Duration</dt><dd>${w.duration_minutes ? w.duration_minutes + ' min' : '—'}</dd>
                        <dt>Location</dt><dd>${escHtml(w.location || '—')}</dd>
                        <dt>Facilitator</dt><dd>${escHtml(w.facilitator || '—')}</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Outcome</h3>
                    <dl class="detail-list">
                        <dt>Requirements</dt><dd>${w.requirements_identified || 0}</dd>
                        <dt>Fit</dt><dd><span class="count-fit">${w.fit_count || 0}</span></dd>
                        <dt>Gap</dt><dd><span class="count-gap">${w.gap_count || 0}</span></dd>
                        <dt>Partial Fit</dt><dd><span class="count-partial">${w.partial_fit_count || 0}</span></dd>
                    </dl>
                </div>
            </div>

            ${w.attendees ? `<div class="card" style="margin-top:16px"><h3>Attendees</h3><p>${escHtml(w.attendees)}</p></div>` : ''}
            ${w.agenda ? `<div class="card" style="margin-top:12px"><h3>Agenda</h3><p style="white-space:pre-line">${escHtml(w.agenda)}</p></div>` : ''}
            ${w.notes ? `<div class="card" style="margin-top:12px"><h3>Notes / Minutes</h3><p style="white-space:pre-line">${escHtml(w.notes)}</p></div>` : ''}
            ${w.decisions ? `<div class="card" style="margin-top:12px"><h3>Decisions</h3><p style="white-space:pre-line">${escHtml(w.decisions)}</p></div>` : ''}
            ${w.action_items ? `<div class="card" style="margin-top:12px"><h3>Action Items</h3><p style="white-space:pre-line">${escHtml(w.action_items)}</p></div>` : ''}

            <div class="card" style="margin-top:20px">
                <div class="card-header">
                    <h3>Requirements from this Workshop</h3>
                </div>
                <div id="workshopRequirements"></div>
            </div>`;

        renderWorkshopRequirements(requirements);
    }

    function renderWorkshopRequirements(requirements) {
        const c = document.getElementById('workshopRequirements');
        if (!requirements || requirements.length === 0) {
            c.innerHTML = '<p style="color:var(--sap-text-secondary);padding:16px">No requirements linked to this workshop yet. Add requirements via the Requirements module and link them to this workshop.</p>';
            return;
        }

        c.innerHTML = `
            <table class="data-table">
                <thead><tr><th>Code</th><th>Title</th><th>Type</th><th>Priority</th><th>Fit/Gap</th><th>Status</th></tr></thead>
                <tbody>
                    ${requirements.map(r => `
                        <tr>
                            <td><strong>${escHtml(r.code || '—')}</strong></td>
                            <td>${escHtml(r.title)}</td>
                            <td>${r.req_type}</td>
                            <td><span class="badge badge-priority-${r.priority}">${r.priority}</span></td>
                            <td>${r.fit_gap ? `<span class="badge badge-${r.fit_gap}">${r.fit_gap}</span>` : '—'}</td>
                            <td><span class="badge badge-${r.status}">${r.status}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>`;
    }

    // ── Scenario Modals ──────────────────────────────────────────────────
    function showCreateModal() {
        App.openModal(`
            <div class="modal-header"><h2>New Business Scenario</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Name *</label><input id="sName" class="form-input" placeholder="e.g. Sevkiyat Süreci"></div>
                <div class="form-group"><label>Description</label><textarea id="sDesc" class="form-input" rows="3"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>SAP Module</label>
                        <select id="sModule" class="form-input">
                            <option value="">— Select —</option>
                            <option value="FI">FI (Finance)</option>
                            <option value="CO">CO (Controlling)</option>
                            <option value="MM">MM (Materials Mgmt)</option>
                            <option value="SD">SD (Sales & Dist.)</option>
                            <option value="PP">PP (Production)</option>
                            <option value="QM">QM (Quality)</option>
                            <option value="PM">PM (Plant Maint.)</option>
                            <option value="WM">WM (Warehouse)</option>
                            <option value="HCM">HCM (Human Capital)</option>
                            <option value="PS">PS (Project System)</option>
                            <option value="Basis">Basis</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Process Area</label>
                        <select id="sArea" class="form-input">
                            ${Object.entries(PROCESS_AREAS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Priority</label>
                        <select id="sPriority" class="form-input">
                            <option value="critical">Critical</option>
                            <option value="high">High</option>
                            <option value="medium" selected>Medium</option>
                            <option value="low">Low</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Owner</label><input id="sOwner" class="form-input" placeholder="Responsible person / team"></div>
                </div>
                <div class="form-group"><label>Workstream</label><input id="sWorkstream" class="form-input"></div>
                <div class="form-group"><label>Notes</label><textarea id="sNotes" class="form-input" rows="2"></textarea></div>
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
            sap_module: document.getElementById('sModule').value,
            process_area: document.getElementById('sArea').value,
            priority: document.getElementById('sPriority').value,
            owner: document.getElementById('sOwner').value,
            workstream: document.getElementById('sWorkstream').value,
            notes: document.getElementById('sNotes').value,
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
                    <div class="form-group"><label>SAP Module</label>
                        <select id="sModule" class="form-input">
                            <option value="">— Select —</option>
                            ${['FI','CO','MM','SD','PP','QM','PM','WM','HCM','PS','Basis'].map(m => `<option value="${m}" ${s.sap_module===m?'selected':''}>${m}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Process Area</label>
                        <select id="sArea" class="form-input">
                            ${Object.entries(PROCESS_AREAS).map(([k, v]) => `<option value="${k}" ${s.process_area===k?'selected':''}>${v}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Status</label>
                        <select id="sStatus" class="form-input">
                            ${['draft','in_analysis','analyzed','approved','on_hold'].map(st => `<option value="${st}" ${s.status===st?'selected':''}>${formatStatus(st)}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Priority</label>
                        <select id="sPriority" class="form-input">
                            ${['critical','high','medium','low'].map(p => `<option value="${p}" ${s.priority===p?'selected':''}>${p}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Owner</label><input id="sOwner" class="form-input" value="${escAttr(s.owner || '')}"></div>
                    <div class="form-group"><label>Workstream</label><input id="sWorkstream" class="form-input" value="${escAttr(s.workstream || '')}"></div>
                </div>
                <div class="form-group"><label>Notes</label><textarea id="sNotes" class="form-input" rows="2">${escHtml(s.notes || '')}</textarea></div>
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
            sap_module: document.getElementById('sModule').value,
            process_area: document.getElementById('sArea').value,
            status: document.getElementById('sStatus').value,
            priority: document.getElementById('sPriority').value,
            owner: document.getElementById('sOwner').value,
            workstream: document.getElementById('sWorkstream').value,
            notes: document.getElementById('sNotes').value,
        };
        try {
            await API.put(`/scenarios/${currentScenario.id}`, body);
            App.closeModal();
            App.toast('Scenario updated', 'success');
            await openDetail(currentScenario.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteScenario(id) {
        if (!confirm('Delete this scenario and all its workshops?')) return;
        try {
            await API.delete(`/scenarios/${id}`);
            App.toast('Scenario deleted', 'success');
            await render();
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Workshop Modals ──────────────────────────────────────────────────
    function showCreateWorkshopModal() {
        App.openModal(`
            <div class="modal-header"><h2>New Workshop / Session</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Title *</label><input id="wTitle" class="form-input" placeholder="e.g. SD Fit-Gap Workshop #1"></div>
                <div class="form-group"><label>Description</label><textarea id="wDesc" class="form-input" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Session Type</label>
                        <select id="wType" class="form-input">
                            ${Object.entries(SESSION_TYPES).map(([k, v]) => `<option value="${k}">${v.icon} ${v.label}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Date</label><input id="wDate" type="datetime-local" class="form-input"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Duration (min)</label><input id="wDuration" type="number" class="form-input" placeholder="60"></div>
                    <div class="form-group"><label>Location</label><input id="wLocation" class="form-input" placeholder="Room / Teams link"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Facilitator</label><input id="wFacilitator" class="form-input"></div>
                    <div class="form-group"><label>Attendees</label><input id="wAttendees" class="form-input" placeholder="Comma-separated names"></div>
                </div>
                <div class="form-group"><label>Agenda</label><textarea id="wAgenda" class="form-input" rows="3"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ScenarioView.doCreateWorkshop()">Create</button>
            </div>
        `);
    }

    async function doCreateWorkshop() {
        const body = {
            title: document.getElementById('wTitle').value,
            description: document.getElementById('wDesc').value,
            session_type: document.getElementById('wType').value,
            session_date: document.getElementById('wDate').value || null,
            duration_minutes: parseInt(document.getElementById('wDuration').value) || null,
            location: document.getElementById('wLocation').value,
            facilitator: document.getElementById('wFacilitator').value,
            attendees: document.getElementById('wAttendees').value,
            agenda: document.getElementById('wAgenda').value,
        };
        try {
            await API.post(`/scenarios/${currentScenario.id}/workshops`, body);
            App.closeModal();
            App.toast('Workshop created', 'success');
            await openDetail(currentScenario.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    function showEditWorkshopModal() {
        const w = currentWorkshop;
        const dateVal = w.session_date ? w.session_date.slice(0, 16) : '';
        App.openModal(`
            <div class="modal-header"><h2>Edit Workshop</h2></div>
            <div class="modal-body">
                <div class="form-group"><label>Title *</label><input id="wTitle" class="form-input" value="${escAttr(w.title)}"></div>
                <div class="form-group"><label>Description</label><textarea id="wDesc" class="form-input" rows="2">${escHtml(w.description || '')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Session Type</label>
                        <select id="wType" class="form-input">
                            ${Object.entries(SESSION_TYPES).map(([k, v]) => `<option value="${k}" ${w.session_type===k?'selected':''}>${v.icon} ${v.label}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group"><label>Status</label>
                        <select id="wStatus" class="form-input">
                            ${['planned','in_progress','completed','cancelled'].map(st => `<option value="${st}" ${w.status===st?'selected':''}>${formatStatus(st)}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Date</label><input id="wDate" type="datetime-local" class="form-input" value="${dateVal}"></div>
                    <div class="form-group"><label>Duration (min)</label><input id="wDuration" type="number" class="form-input" value="${w.duration_minutes || ''}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Location</label><input id="wLocation" class="form-input" value="${escAttr(w.location || '')}"></div>
                    <div class="form-group"><label>Facilitator</label><input id="wFacilitator" class="form-input" value="${escAttr(w.facilitator || '')}"></div>
                </div>
                <div class="form-group"><label>Attendees</label><input id="wAttendees" class="form-input" value="${escAttr(w.attendees || '')}"></div>
                <div class="form-group"><label>Agenda</label><textarea id="wAgenda" class="form-input" rows="3">${escHtml(w.agenda || '')}</textarea></div>
                <div class="form-group"><label>Notes / Minutes</label><textarea id="wNotes" class="form-input" rows="3">${escHtml(w.notes || '')}</textarea></div>
                <div class="form-group"><label>Decisions</label><textarea id="wDecisions" class="form-input" rows="2">${escHtml(w.decisions || '')}</textarea></div>
                <div class="form-group"><label>Action Items</label><textarea id="wActions" class="form-input" rows="2">${escHtml(w.action_items || '')}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Fit Count</label><input id="wFit" type="number" class="form-input" value="${w.fit_count || 0}"></div>
                    <div class="form-group"><label>Gap Count</label><input id="wGap" type="number" class="form-input" value="${w.gap_count || 0}"></div>
                    <div class="form-group"><label>Partial Fit</label><input id="wPartial" type="number" class="form-input" value="${w.partial_fit_count || 0}"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ScenarioView.doEditWorkshop()">Save</button>
            </div>
        `);
    }

    async function doEditWorkshop() {
        const body = {
            title: document.getElementById('wTitle').value,
            description: document.getElementById('wDesc').value,
            session_type: document.getElementById('wType').value,
            status: document.getElementById('wStatus').value,
            session_date: document.getElementById('wDate').value || null,
            duration_minutes: parseInt(document.getElementById('wDuration').value) || null,
            location: document.getElementById('wLocation').value,
            facilitator: document.getElementById('wFacilitator').value,
            attendees: document.getElementById('wAttendees').value,
            agenda: document.getElementById('wAgenda').value,
            notes: document.getElementById('wNotes').value,
            decisions: document.getElementById('wDecisions').value,
            action_items: document.getElementById('wActions').value,
            fit_count: parseInt(document.getElementById('wFit').value) || 0,
            gap_count: parseInt(document.getElementById('wGap').value) || 0,
            partial_fit_count: parseInt(document.getElementById('wPartial').value) || 0,
        };
        try {
            await API.put(`/workshops/${currentWorkshop.id}`, body);
            App.closeModal();
            App.toast('Workshop updated', 'success');
            await openWorkshop(currentWorkshop.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteWorkshop(id) {
        if (!confirm('Delete this workshop?')) return;
        try {
            await API.delete(`/workshops/${id}`);
            App.toast('Workshop deleted', 'success');
            await openDetail(currentScenario.id);
        } catch (err) { App.toast(err.message, 'error'); }
    }

    // ── Utility ──────────────────────────────────────────────────────────
    function escHtml(s) {
        const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
    }
    function escAttr(s) { return (s || '').replace(/"/g, '&quot;'); }
    function formatStatus(s) { return (s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }

    return {
        render, loadScenarios, openDetail, showCreateModal, doCreate, showEditModal, doEdit, deleteScenario,
        showCreateWorkshopModal, doCreateWorkshop, openWorkshop, showEditWorkshopModal, doEditWorkshop, deleteWorkshop,
    };
})();
