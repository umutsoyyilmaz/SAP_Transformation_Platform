const ChangeManagementView = (() => {
    let _container = null;
    let _tab = 'cockpit';
    let _state = {
        analytics: { summary: {}, status_counts: {}, model_counts: {} },
        changeRequests: [],
        boards: [],
        decisions: [],
        windows: [],
        exceptions: [],
        pirs: [],
    };

    function _program() {
        return (typeof App !== 'undefined' && App.getActiveProgram) ? App.getActiveProgram() : null;
    }

    function _project() {
        return (typeof App !== 'undefined' && App.getActiveProject) ? App.getActiveProject() : null;
    }

    function _ctxQuery() {
        const program = _program();
        const project = _project();
        const params = new URLSearchParams();
        if (program?.id) params.set('program_id', String(program.id));
        if (project?.id) params.set('project_id', String(project.id));
        const query = params.toString();
        return query ? `?${query}` : '';
    }

    function _esc(value) {
        const div = document.createElement('div');
        div.textContent = value ?? '';
        return div.innerHTML;
    }

    function _badge(status) {
        const map = {
            draft: 'badge badge--gray',
            submitted: 'badge badge--blue',
            assessed: 'badge badge--yellow',
            cab_pending: 'badge badge--orange',
            approved: 'badge badge--green',
            deferred: 'badge badge--gray',
            rejected: 'badge badge--red',
            ecab_authorized: 'badge badge--orange',
            scheduled: 'badge badge--blue',
            implementing: 'badge badge--orange',
            implemented: 'badge badge--green',
            validated: 'badge badge--green',
            backed_out: 'badge badge--red',
            pir_pending: 'badge badge--yellow',
            closed: 'badge badge--green',
        };
        return `<span class="${map[status] || 'badge'}">${_esc(status || 'unknown')}</span>`;
    }

    async function _load() {
        const query = _ctxQuery();
        const [analytics, changeRequests, boards, decisions, windows, exceptions, pirs] = await Promise.all([
            API.get(`/change-management/analytics${query}`),
            API.get(`/change-management/change-requests${query}`),
            API.get(`/change-management/boards${query}`),
            API.get(`/change-management/decisions${query}`),
            API.get(`/change-management/windows${query}`),
            API.get(`/change-management/exceptions${query}`),
            API.get(`/change-management/pir${query}`),
        ]);
        _state = {
            analytics: analytics || { summary: {}, status_counts: {}, model_counts: {} },
            changeRequests: changeRequests.items || [],
            boards: boards.items || [],
            decisions: decisions.items || [],
            windows: windows.items || [],
            exceptions: exceptions.items || [],
            pirs: pirs.items || [],
        };
    }

    function _summaryCard(value, label, tone, sub) {
        return `
            <div class="discover-summary-card${tone ? ` discover-summary-card--${tone}` : ''}">
                <div class="discover-summary-card__value">${_esc(String(value))}</div>
                <div class="discover-summary-card__label">${_esc(label)}</div>
                ${sub ? `<div class="discover-summary-card__sub">${_esc(sub)}</div>` : ''}
            </div>`;
    }

    function _renderSummary() {
        const s = _state.analytics.summary || {};
        const successRate = s.change_success_rate || 0;
        const backoutRate = s.backout_rate || 0;
        const emergencyRatio = s.emergency_ratio || 0;
        return `
            <div class="discover-summary-strip" style="margin-bottom:20px;">
                ${_summaryCard(s.total_changes || 0, 'Total RFC', s.total_changes ? 'info' : 'default', 'All change requests')}
                ${_summaryCard(`${successRate}%`, 'Success Rate', successRate >= 80 ? 'success' : successRate >= 50 ? 'warning' : 'default', 'Implemented without rollback')}
                ${_summaryCard(`${emergencyRatio}%`, 'Emergency %', emergencyRatio > 20 ? 'warning' : 'success', 'Of total RFCs')}
                ${_summaryCard(`${backoutRate}%`, 'Backout Rate', backoutRate > 10 ? 'warning' : 'success', 'Rolled back changes')}
                ${_summaryCard(s.freeze_exceptions || 0, 'Freeze Exceptions', s.freeze_exceptions > 0 ? 'warning' : 'success', 'Exceptions raised')}
                ${_summaryCard(s.pir_overdue || 0, 'PIR Overdue', s.pir_overdue > 0 ? 'warning' : 'success', 'Awaiting post-review')}
            </div>
        `;
    }

    function _renderTabs() {
        const tabs = [
            { id: 'cockpit',  step: '01', eyebrow: 'Register',  label: 'Change Cockpit'  },
            { id: 'cab',      step: '02', eyebrow: 'Governance', label: 'CAB Workspace'   },
            { id: 'calendar', step: '03', eyebrow: 'Control',    label: 'Change Calendar' },
            { id: 'pir',      step: '04', eyebrow: 'Closure',    label: 'PIR Queue'       },
        ];
        return `
            <div class="explore-stage-nav discover-stage-nav" style="margin-bottom:20px;">
                <div class="explore-stage-nav__items">
                    ${tabs.map((t) => `
                        <button type="button"
                            class="explore-stage-link${_tab === t.id ? ' explore-stage-link--active' : ''}"
                            data-tab="${t.id}"
                            onclick="ChangeManagementView.switchTab('${t.id}')">
                            <span class="explore-stage-link__step">${t.step}</span>
                            <span class="explore-stage-link__body">
                                <span class="explore-stage-link__eyebrow">${t.eyebrow}</span>
                                <span class="explore-stage-link__label">${t.label}</span>
                            </span>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }

    function _renderCockpit() {
        const rows = _state.changeRequests.map((row) => `
            <tr>
                <td>
                    <strong>${_esc(row.code)}</strong>
                    <div style="color:var(--sap-text-secondary,#667085);font-size:12px;margin-top:2px;">${_esc(row.title)}</div>
                </td>
                <td>${_badge(row.status)}</td>
                <td>${_esc(row.change_model)}</td>
                <td>${_esc(row.change_domain)}</td>
                <td>${_esc(row.priority)}</td>
                <td>${_esc(row.risk_level)}</td>
                <td style="white-space:nowrap;">
                    <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ChangeManagementView.openChangeDetail(${row.id})">Detail</button>
                    ${row.available_actions?.includes('submit') ? `<button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ChangeManagementView.submitChange(${row.id})">Submit</button>` : ''}
                    ${row.available_actions?.includes('assess') ? `<button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ChangeManagementView.openAssessModal(${row.id})">Assess</button>` : ''}
                    ${row.available_actions?.includes('route') ? `<button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ChangeManagementView.openDecisionModal(${row.id}, true)">Route</button>` : ''}
                    ${row.available_actions?.includes('create_pir') ? `<button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ChangeManagementView.openPirCreateModal(${row.id})">PIR</button>` : ''}
                </td>
            </tr>
        `).join('');
        return `
            <div class="section-card">
                <div class="section-card__header">
                    <div style="flex:1;">
                        <h3>RFC Register</h3>
                        <p class="discover-section-lead" style="margin-top:2px;">Canonical change requests across Explore, Realize, Deploy and Run.</p>
                    </div>
                    <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="ChangeManagementView.openCreateModal()">+ New RFC</button>
                </div>
                <div class="section-card__body" style="padding:0;overflow-x:auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>RFC</th>
                                <th>Status</th>
                                <th>Model</th>
                                <th>Domain</th>
                                <th>Priority</th>
                                <th>Risk</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>${rows || `<tr><td colspan="7" style="padding:24px;text-align:center;color:var(--sap-text-secondary);">No change requests yet.</td></tr>`}</tbody>
                    </table>
                </div>
            </div>
        `;
    }

    function _renderCab() {
        const pending = _state.changeRequests.filter((row) => row.status === 'cab_pending');
        const emptyRow = (cols, msg) => `<tr><td colspan="${cols}" style="padding:24px;text-align:center;color:var(--sap-text-secondary);">${msg}</td></tr>`;
        return `
            <div class="discover-summary-strip" style="margin-bottom:20px;">
                ${_summaryCard(_state.boards.length, 'Boards', _state.boards.length ? 'info' : 'default', 'CAB / ECAB profiles')}
                ${_summaryCard(pending.length, 'Pending Queue', pending.length ? 'warning' : 'success', 'Awaiting board decision')}
                ${_summaryCard(_state.decisions.length, 'Decisions', 'info', 'Recorded this period')}
            </div>
            <div class="section-card" style="margin-bottom:16px;">
                <div class="section-card__header">
                    <div style="flex:1;">
                        <h3>Boards</h3>
                        <p class="discover-section-lead" style="margin-top:2px;">CAB/ECAB profiles on top of Committee master data.</p>
                    </div>
                    <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="ChangeManagementView.openBoardModal()">+ New Board</button>
                </div>
                <div class="section-card__body" style="padding:0;overflow-x:auto;">
                    <table class="data-table">
                        <thead><tr><th>Name</th><th>Kind</th><th>Quorum</th><th>Meetings</th></tr></thead>
                        <tbody>
                            ${_state.boards.map((row) => `
                                <tr>
                                    <td>${_esc(row.name)}</td>
                                    <td>${_badge(row.board_kind)}</td>
                                    <td>${_esc(String(row.quorum_min))}</td>
                                    <td>${_esc(String(row.meeting_count || 0))}</td>
                                </tr>
                            `).join('') || emptyRow(4, 'No boards configured.')}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="section-card" style="margin-bottom:16px;">
                <div class="section-card__header">
                    <div style="flex:1;">
                        <h3>Pending CAB Queue</h3>
                        <p class="discover-section-lead" style="margin-top:2px;">RFCs waiting for board decision.</p>
                    </div>
                    ${pending.length ? `<span class="badge badge--orange" style="font-size:13px;">${pending.length} pending</span>` : ''}
                </div>
                <div class="section-card__body" style="padding:0;overflow-x:auto;">
                    <table class="data-table">
                        <thead><tr><th>RFC</th><th>Board</th><th>Priority</th><th>Decision</th></tr></thead>
                        <tbody>
                            ${pending.map((row) => `
                                <tr>
                                    <td>
                                        <strong>${_esc(row.code)}</strong>
                                        <div style="color:var(--sap-text-secondary);font-size:12px;margin-top:2px;">${_esc(row.title)}</div>
                                    </td>
                                    <td>${_esc(row.board?.name || 'Unassigned')}</td>
                                    <td>${_esc(row.priority)}</td>
                                    <td><button class="pg-btn pg-btn--primary pg-btn--sm" onclick="ChangeManagementView.openDecisionModal(${row.id}, false)">Record Decision</button></td>
                                </tr>
                            `).join('') || emptyRow(4, 'No RFC is waiting for CAB.')}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="section-card">
                <div class="section-card__header">
                    <h3>Recent Decisions</h3>
                </div>
                <div class="section-card__body" style="padding:0;overflow-x:auto;">
                    <table class="data-table">
                        <thead><tr><th>Decision</th><th>RFC</th><th>Rationale</th></tr></thead>
                        <tbody>
                            ${_state.decisions.slice(0, 10).map((row) => `
                                <tr>
                                    <td>${_badge(row.decision)}</td>
                                    <td>${_esc(String(row.change_request_id))}</td>
                                    <td>${_esc(row.rationale || row.conditions || '')}</td>
                                </tr>
                            `).join('') || emptyRow(3, 'No decisions recorded.')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    function _renderCalendar() {
        const pendingExceptions = _state.exceptions.filter((e) => e.status === 'pending');
        const emptyRow = (cols, msg) => `<tr><td colspan="${cols}" style="padding:24px;text-align:center;color:var(--sap-text-secondary);">${msg}</td></tr>`;
        return `
            <div class="discover-summary-strip" style="margin-bottom:20px;">
                ${_summaryCard(_state.windows.length, 'Calendar Windows', _state.windows.length ? 'info' : 'default', 'Freeze, blackout, permitted')}
                ${_summaryCard(pendingExceptions.length, 'Pending Exceptions', pendingExceptions.length ? 'warning' : 'success', 'Awaiting approval')}
                ${_summaryCard(_state.exceptions.length, 'Total Exceptions', 'default', 'All periods')}
            </div>
            <div class="section-card" style="margin-bottom:16px;">
                <div class="section-card__header">
                    <div style="flex:1;">
                        <h3>Change Windows</h3>
                        <p class="discover-section-lead" style="margin-top:2px;">Freeze, blackout and permitted change windows.</p>
                    </div>
                    <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="ChangeManagementView.openWindowModal()">+ New Window</button>
                </div>
                <div class="section-card__body" style="padding:0;overflow-x:auto;">
                    <table class="data-table">
                        <thead><tr><th>Title</th><th>Type</th><th>Start</th><th>End</th></tr></thead>
                        <tbody>
                            ${_state.windows.map((row) => `
                                <tr>
                                    <td>${_esc(row.title)}</td>
                                    <td>${_badge(row.window_type)}</td>
                                    <td>${_esc(row.start_at || '—')}</td>
                                    <td>${_esc(row.end_at || '—')}</td>
                                </tr>
                            `).join('') || emptyRow(4, 'No calendar windows configured.')}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="section-card">
                <div class="section-card__header">
                    <div style="flex:1;">
                        <h3>Freeze Exceptions</h3>
                        <p class="discover-section-lead" style="margin-top:2px;">Exception requests raised against active freeze windows.</p>
                    </div>
                    ${pendingExceptions.length ? `<span class="badge badge--orange" style="font-size:13px;">${pendingExceptions.length} pending</span>` : ''}
                </div>
                <div class="section-card__body" style="padding:0;overflow-x:auto;">
                    <table class="data-table">
                        <thead><tr><th>RFC</th><th>Status</th><th>Justification</th><th>Action</th></tr></thead>
                        <tbody>
                            ${_state.exceptions.map((row) => `
                                <tr>
                                    <td>${_esc(String(row.change_request_id))}</td>
                                    <td>${_badge(row.status)}</td>
                                    <td>${_esc(row.justification || '')}</td>
                                    <td style="white-space:nowrap;">
                                        ${row.status === 'pending' ? `
                                            <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ChangeManagementView.decideException(${row.id}, true)">Approve</button>
                                            <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ChangeManagementView.decideException(${row.id}, false)">Reject</button>
                                        ` : ''}
                                    </td>
                                </tr>
                            `).join('') || emptyRow(4, 'No exceptions raised.')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    function _renderPir() {
        const open = _state.pirs.filter((p) => p.status !== 'completed');
        const completed = _state.pirs.filter((p) => p.status === 'completed');
        const emptyRow = (cols, msg) => `<tr><td colspan="${cols}" style="padding:24px;text-align:center;color:var(--sap-text-secondary);">${msg}</td></tr>`;
        return `
            <div class="discover-summary-strip" style="margin-bottom:20px;">
                ${_summaryCard(_state.pirs.length, 'Total PIRs', _state.pirs.length ? 'info' : 'default', 'All post-implementation reviews')}
                ${_summaryCard(open.length, 'Open PIRs', open.length ? 'warning' : 'success', 'Pending completion')}
                ${_summaryCard(completed.length, 'Completed', completed.length ? 'success' : 'default', 'Formally closed')}
            </div>
            <div class="section-card">
                <div class="section-card__header">
                    <div style="flex:1;">
                        <h3>PIR Queue</h3>
                        <p class="discover-section-lead" style="margin-top:2px;">Post-implementation reviews required before formal closure.</p>
                    </div>
                    ${open.length ? `<span class="badge badge--orange" style="font-size:13px;">${open.length} open</span>` : ''}
                </div>
                <div class="section-card__body" style="padding:0;overflow-x:auto;">
                    <table class="data-table">
                        <thead><tr><th>PIR</th><th>RFC</th><th>Status</th><th>Outcome</th><th>Action</th></tr></thead>
                        <tbody>
                            ${_state.pirs.map((row) => `
                                <tr>
                                    <td>${_esc(`PIR-${row.id}`)}</td>
                                    <td>${_esc(String(row.change_request_id))}</td>
                                    <td>${_badge(row.status)}</td>
                                    <td>${_esc(row.outcome || '—')}</td>
                                    <td>
                                        <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ChangeManagementView.openPirCompleteModal(${row.id})">
                                            ${row.status === 'completed' ? 'View' : 'Complete'}
                                        </button>
                                    </td>
                                </tr>
                            `).join('') || emptyRow(5, 'No PIR records created.')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    function _renderBody() {
        if (_tab === 'cab') return _renderCab();
        if (_tab === 'calendar') return _renderCalendar();
        if (_tab === 'pir') return _renderPir();
        return _renderCockpit();
    }

    async function render(container) {
        _container = container || document.getElementById('mainContent');
        const program = _program();
        const project = _project();
        if (!program || !project) {
            _container.innerHTML = `
                <div class="empty-state">
                    <h2>Enterprise Change Management</h2>
                    <p>Select a program and project to work with RFCs, CAB and PIR queues.</p>
                </div>
            `;
            return;
        }

        _container.innerHTML = `<div class="spinner"></div>`;
        try {
            await _load();
            const s = _state.analytics.summary || {};
            const overallTone = (s.pir_overdue > 0 || s.backout_rate > 10) ? 'warning' : 'success';
            const overallLabel = overallTone === 'success' ? 'Change Health: Good' : 'Change Health: Review Needed';
            _container.innerHTML = `
                <div class="pg-view-header" style="margin-bottom:16px;">
                    <div class="discover-workspace-heading">
                        <h1 style="margin:0;font-size:22px;font-weight:700;">Enterprise Change Management</h1>
                        <p class="discover-section-lead">
                            Canonical RFC, CAB, freeze control and PIR flow for
                            <strong>${_esc(program.name)}</strong> / ${_esc(project.name)}.
                        </p>
                    </div>
                    <div class="discover-gate-banner discover-gate-banner--${overallTone}" style="margin-top:12px;">
                        <div class="gate-criteria-row">
                            <span class="gate-criterion ${overallTone === 'success' ? 'passed' : 'failed'}">${overallLabel}</span>
                            ${s.freeze_exceptions > 0 ? `<span class="gate-criterion failed">⚠ ${s.freeze_exceptions} freeze exception${s.freeze_exceptions > 1 ? 's' : ''} open</span>` : '<span class="gate-criterion passed">✅ No freeze exceptions</span>'}
                            ${s.pir_overdue > 0 ? `<span class="gate-criterion failed">⚠ ${s.pir_overdue} PIR overdue</span>` : '<span class="gate-criterion passed">✅ PIR queue clear</span>'}
                        </div>
                    </div>
                </div>
                ${_renderSummary()}
                ${_renderTabs()}
                ${_renderBody()}
            `;
        } catch (err) {
            _container.innerHTML = `<div class="empty-state"><h2>Load failed</h2><p>${_esc(err.message || 'Change Management data could not be loaded.')}</p></div>`;
        }
    }

    function switchTab(tab) {
        _tab = tab;
        render(_container);
    }

    function _modalShell(title, body, footer) {
        return `
            <div class="modal-header">
                <h3>${_esc(title)}</h3>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <div class="modal-body">${body}</div>
            <div class="modal-footer">${footer}</div>
        `;
    }

    function openCreateModal() {
        App.openModal(_modalShell(
            'New RFC',
            `
                <label>Title<input id="cmTitle" class="form-control" /></label>
                <label>Change Model
                    <select id="cmModel" class="form-control">
                        <option value="normal">Normal</option>
                        <option value="standard">Standard</option>
                        <option value="emergency">Emergency</option>
                    </select>
                </label>
                <label>Domain
                    <select id="cmDomain" class="form-control">
                        <option value="config">Config</option>
                        <option value="scope">Scope</option>
                        <option value="development">Development</option>
                        <option value="data">Data</option>
                        <option value="transport">Transport</option>
                        <option value="authorization">Authorization</option>
                        <option value="cutover">Cutover</option>
                        <option value="hypercare">Hypercare</option>
                    </select>
                </label>
                <label>Priority
                    <select id="cmPriority" class="form-control">
                        <option value="P3">P3</option>
                        <option value="P1">P1</option>
                        <option value="P2">P2</option>
                        <option value="P4">P4</option>
                    </select>
                </label>
                <label>Description<textarea id="cmDescription" class="form-control" rows="4"></textarea></label>
            `,
            `
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ChangeManagementView.createChange()">Create</button>
            `
        ));
    }

    async function createChange() {
        const program = _program();
        const project = _project();
        const payload = {
            title: document.getElementById('cmTitle')?.value,
            change_model: document.getElementById('cmModel')?.value,
            change_domain: document.getElementById('cmDomain')?.value,
            priority: document.getElementById('cmPriority')?.value,
            description: document.getElementById('cmDescription')?.value,
            program_id: program?.id,
            project_id: project?.id,
        };
        try {
            await API.post('/change-management/change-requests', payload);
            App.closeModal();
            App.toast('RFC created', 'success');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'RFC creation failed', 'error');
        }
    }

    async function submitChange(changeRequestId) {
        try {
            await API.post(`/change-management/change-requests/${changeRequestId}/submit`, {});
            App.toast('RFC submitted', 'success');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'Submit failed', 'error');
        }
    }

    function openAssessModal(changeRequestId) {
        App.openModal(_modalShell(
            'Assess RFC',
            `
                <label>Risk Level
                    <select id="cmRisk" class="form-control">
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                    </select>
                </label>
                <label>Impact Summary<textarea id="cmImpact" class="form-control" rows="3"></textarea></label>
                <label>Implementation Plan<textarea id="cmImpl" class="form-control" rows="3"></textarea></label>
                <label>Rollback Plan<textarea id="cmRollback" class="form-control" rows="3"></textarea></label>
            `,
            `
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ChangeManagementView.assessChange(${changeRequestId})">Save Assessment</button>
            `
        ));
    }

    async function assessChange(changeRequestId) {
        const payload = {
            risk_level: document.getElementById('cmRisk')?.value,
            impact_summary: document.getElementById('cmImpact')?.value,
            implementation_plan: document.getElementById('cmImpl')?.value,
            rollback_plan: document.getElementById('cmRollback')?.value,
        };
        try {
            await API.post(`/change-management/change-requests/${changeRequestId}/assess`, payload);
            App.closeModal();
            App.toast('RFC assessed', 'success');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'Assessment failed', 'error');
        }
    }

    async function openBoardModal() {
        const program = _program();
        const project = _project();
        let committeeOptions = '<option value="">Loading…</option>';
        try {
            const qs = project?.id ? `?project_id=${project.id}` : '';
            const data = await API.get(`/programs/${program.id}/committees${qs}`);
            const items = data.items || data || [];
            if (items.length === 0) {
                committeeOptions = '<option value="">No committees found — create one first</option>';
            } else {
                committeeOptions = items.map((c) => `<option value="${c.id}">${_esc(c.name)}</option>`).join('');
            }
        } catch (_) {
            committeeOptions = '<option value="">Could not load committees</option>';
        }
        App.openModal(_modalShell(
            'New Board Profile',
            `
                <label>Committee
                    <select id="cmCommitteeId" class="form-control">${committeeOptions}</select>
                </label>
                <label>Name<input id="cmBoardName" class="form-control" placeholder="Leave blank to use committee name" /></label>
                <label>Kind
                    <select id="cmBoardKind" class="form-control">
                        <option value="cab">CAB</option>
                        <option value="ecab">ECAB</option>
                    </select>
                </label>
                <label>Quorum<input id="cmBoardQuorum" class="form-control" type="number" min="1" value="1" /></label>
            `,
            `
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ChangeManagementView.createBoard()">Create</button>
            `
        ));
    }

    async function createBoard() {
        const program = _program();
        const project = _project();
        const payload = {
            committee_id: document.getElementById('cmCommitteeId')?.value,
            name: document.getElementById('cmBoardName')?.value || undefined,
            board_kind: document.getElementById('cmBoardKind')?.value,
            quorum_min: document.getElementById('cmBoardQuorum')?.value,
            program_id: program?.id,
            project_id: project?.id,
        };
        try {
            await API.post('/change-management/boards', payload);
            App.closeModal();
            App.toast('Board created', 'success');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'Board creation failed', 'error');
        }
    }

    function openDecisionModal(changeRequestId, routeOnly) {
        const boardOptions = _state.boards.map((row) => `<option value="${row.id}">${_esc(row.name)} (${_esc(row.board_kind)})</option>`).join('');
        const routeFooter = routeOnly
            ? `<button class="btn btn-primary" onclick="ChangeManagementView.routeChange(${changeRequestId})">Route to Board</button>`
            : `<button class="btn btn-primary" onclick="ChangeManagementView.recordDecision(${changeRequestId})">Record Decision</button>`;
        App.openModal(_modalShell(
            routeOnly ? 'Route RFC to Board' : 'Record CAB Decision',
            `
                <label>Board
                    <select id="cmDecisionBoard" class="form-control">${boardOptions}</select>
                </label>
                ${routeOnly ? '' : `
                    <label>Decision
                        <select id="cmDecisionValue" class="form-control">
                            <option value="approved">Approved</option>
                            <option value="approved_with_conditions">Approved with Conditions</option>
                            <option value="deferred">Deferred</option>
                            <option value="rejected">Rejected</option>
                            <option value="emergency_authorized">Emergency Authorized</option>
                        </select>
                    </label>
                    <label>Rationale<textarea id="cmDecisionRationale" class="form-control" rows="3"></textarea></label>
                `}
            `,
            `
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                ${routeFooter}
            `
        ));
    }

    async function routeChange(changeRequestId) {
        try {
            await API.post(`/change-management/change-requests/${changeRequestId}/route`, {
                board_profile_id: document.getElementById('cmDecisionBoard')?.value,
            });
            App.closeModal();
            App.toast('RFC routed to board', 'success');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'Routing failed', 'error');
        }
    }

    async function recordDecision(changeRequestId) {
        try {
            await API.post(`/change-management/change-requests/${changeRequestId}/decisions`, {
                board_profile_id: document.getElementById('cmDecisionBoard')?.value,
                decision: document.getElementById('cmDecisionValue')?.value,
                rationale: document.getElementById('cmDecisionRationale')?.value,
            });
            App.closeModal();
            App.toast('Decision recorded', 'success');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'Decision failed', 'error');
        }
    }

    function openWindowModal() {
        App.openModal(_modalShell(
            'New Calendar Window',
            `
                <label>Title<input id="cmWindowTitle" class="form-control" /></label>
                <label>Type
                    <select id="cmWindowType" class="form-control">
                        <option value="change_window">Change Window</option>
                        <option value="freeze">Freeze</option>
                        <option value="blackout">Blackout</option>
                    </select>
                </label>
                <label>Start<input id="cmWindowStart" class="form-control" type="datetime-local" /></label>
                <label>End<input id="cmWindowEnd" class="form-control" type="datetime-local" /></label>
            `,
            `
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ChangeManagementView.createWindow()">Create</button>
            `
        ));
    }

    async function createWindow() {
        const program = _program();
        const project = _project();
        try {
            await API.post('/change-management/windows', {
                title: document.getElementById('cmWindowTitle')?.value,
                window_type: document.getElementById('cmWindowType')?.value,
                start_at: document.getElementById('cmWindowStart')?.value,
                end_at: document.getElementById('cmWindowEnd')?.value,
                program_id: program?.id,
                project_id: project?.id,
            });
            App.closeModal();
            App.toast('Window created', 'success');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'Window creation failed', 'error');
        }
    }

    async function decideException(exceptionId, approve) {
        const path = approve ? 'approve' : 'reject';
        try {
            await API.post(`/change-management/exceptions/${exceptionId}/${path}`, approve ? {} : { rejection_reason: 'Rejected from calendar console' });
            App.toast(`Exception ${approve ? 'approved' : 'rejected'}`, approve ? 'success' : 'warning');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'Exception decision failed', 'error');
        }
    }

    function openPirCreateModal(changeRequestId) {
        App.openModal(_modalShell(
            'Create PIR',
            `<label>Summary<textarea id="cmPirSummary" class="form-control" rows="4"></textarea></label>`,
            `
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="ChangeManagementView.createPir(${changeRequestId})">Create PIR</button>
            `
        ));
    }

    async function createPir(changeRequestId) {
        try {
            await API.post(`/change-management/change-requests/${changeRequestId}/pir`, {
                summary: document.getElementById('cmPirSummary')?.value,
            });
            App.closeModal();
            App.toast('PIR created', 'success');
            _tab = 'pir';
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'PIR creation failed', 'error');
        }
    }

    function openPirCompleteModal(pirId) {
        const row = _state.pirs.find((item) => item.id === pirId);
        App.openModal(_modalShell(
            row?.status === 'completed' ? 'PIR Detail' : 'Complete PIR',
            `
                <label>Outcome
                    <select id="cmPirOutcome" class="form-control" ${row?.status === 'completed' ? 'disabled' : ''}>
                        <option value="successful">Successful</option>
                        <option value="successful_with_issues">Successful with Issues</option>
                        <option value="rolled_back">Rolled Back</option>
                        <option value="failed">Failed</option>
                    </select>
                </label>
                <label>Summary<textarea id="cmPirCompleteSummary" class="form-control" rows="4" ${row?.status === 'completed' ? 'disabled' : ''}>${_esc(row?.summary || '')}</textarea></label>
                ${row?.status === 'completed' ? '' : '<label><input id="cmPirLesson" type="checkbox" /> Create lesson learned</label>'}
            `,
            row?.status === 'completed'
                ? `<button class="btn btn-primary" onclick="App.closeModal()">Close</button>`
                : `
                    <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button class="btn btn-primary" onclick="ChangeManagementView.completePir(${pirId})">Complete PIR</button>
                `
        ));
    }

    async function completePir(pirId) {
        try {
            await API.post(`/change-management/pir/${pirId}/complete`, {
                outcome: document.getElementById('cmPirOutcome')?.value,
                summary: document.getElementById('cmPirCompleteSummary')?.value,
                create_lesson_learned: Boolean(document.getElementById('cmPirLesson')?.checked),
            });
            App.closeModal();
            App.toast('PIR completed', 'success');
            await render(_container);
        } catch (err) {
            App.toast(err.message || 'PIR completion failed', 'error');
        }
    }

    async function openChangeDetail(changeRequestId) {
        try {
            const detail = await API.get(`/change-management/change-requests/${changeRequestId}?include=children${_ctxQuery() ? `&${_ctxQuery().slice(1)}` : ''}`);
            App.openModal(_modalShell(
                `${detail.code} · ${detail.title}`,
                `
                    <p><strong>Status:</strong> ${_esc(detail.status)}</p>
                    <p><strong>Model / Domain:</strong> ${_esc(detail.change_model)} / ${_esc(detail.change_domain)}</p>
                    <p><strong>Description:</strong> ${_esc(detail.description || '')}</p>
                    <p><strong>Impact:</strong> ${_esc(detail.impact_summary || '')}</p>
                    <p><strong>Rollback:</strong> ${_esc(detail.rollback_plan || '')}</p>
                    <p><strong>Conflicts:</strong> ${_esc(String(detail.window_conflicts?.length || 0))}</p>
                    <p><strong>Links:</strong> ${_esc(String(detail.links?.length || 0))}</p>
                    <p><strong>Events:</strong> ${_esc(String(detail.events?.length || 0))}</p>
                `,
                `<button class="btn btn-primary" onclick="App.closeModal()">Close</button>`
            ));
        } catch (err) {
            App.toast(err.message || 'Detail load failed', 'error');
        }
    }

    return {
        render,
        switchTab,
        openCreateModal,
        createChange,
        submitChange,
        openAssessModal,
        assessChange,
        openBoardModal,
        createBoard,
        openDecisionModal,
        routeChange,
        recordDecision,
        openWindowModal,
        createWindow,
        decideException,
        openPirCreateModal,
        createPir,
        openPirCompleteModal,
        completePir,
        openChangeDetail,
    };
})();
