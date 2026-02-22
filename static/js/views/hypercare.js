/**
 * Hypercare War Room Dashboard — FDD-B03, S4-01.
 *
 * Provides:
 *  - P1/P2/P3/P4 open incident priority cards
 *  - SLA breach counter
 *  - Incident table with status/severity filters
 *  - Create incident modal
 *  - Comment thread panel
 *  - Change requests table with approve/reject actions
 *
 * Dependencies:
 *  - App.getActiveProgram()  → { id, name }
 *  - GET /api/v1/run-sustain/plans/:planId/hypercare/metrics
 *  - GET /api/v1/run-sustain/plans/:planId/hypercare/incidents
 *  - POST/PUT endpoints per hypercare_bp
 */

const HypercareView = (() => {
    // ── State ─────────────────────────────────────────────────────────────────
    let _planId = null;
    let _incidents = [];
    let _changeRequests = [];
    let _metrics = {};
    let _container = null;
    let _statusFilter = '';
    let _severityFilter = '';

    // ── Helpers ───────────────────────────────────────────────────────────────

    const API = (path, opts = {}) =>
        fetch(path, {
            headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
            ...opts,
        }).then(r => r.json().then(d => ({ ok: r.ok, status: r.status, data: d })));

    const severityColor = {
        P1: 'badge--red',
        P2: 'badge--orange',
        P3: 'badge--yellow',
        P4: 'badge--blue',
    };

    const slaIcon = (inc) => {
        if (inc.sla_resolution_breached) return '🔴';
        if (inc.sla_response_breached) return '🟡';
        return '🟢';
    };

    function toast(msg, type = 'info') {
        if (window.Toast) { window.Toast[type](msg); }
    }

    // ── Data Fetching ─────────────────────────────────────────────────────────

    async function _loadMetrics() {
        const { ok, data } = await API(`/api/v1/run-sustain/plans/${_planId}/hypercare/metrics`);
        if (ok) _metrics = data;
    }

    async function _loadIncidents() {
        let url = `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents?_t=${Date.now()}`;
        if (_statusFilter) url += `&status=${encodeURIComponent(_statusFilter)}`;
        if (_severityFilter) url += `&severity=${encodeURIComponent(_severityFilter)}`;
        const { ok, data } = await API(url);
        if (ok) _incidents = data.items || [];
    }

    async function _loadChangeRequests() {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/change-requests`
        );
        if (ok) _changeRequests = data.items || [];
    }

    async function _resolveActivePlan(programId) {
        // Fetch the active (or first) cutover plan for the program
        const { ok, data } = await API(
            `/api/v1/run-sustain/cutover-plans?program_id=${programId}`
        );
        if (!ok || !data.items || data.items.length === 0) return null;
        return data.items[0].id;
    }

    // ── Rendering ─────────────────────────────────────────────────────────────

    function _renderMetricsCards() {
        const ob = _metrics.open_by_priority || {};
        return `
        <div class="hypercare-metrics-grid">
            <div class="metric-card metric-card--p1">
                <div class="metric-card__value">${ob.P1 || 0}</div>
                <div class="metric-card__label">P1 Open</div>
            </div>
            <div class="metric-card metric-card--p2">
                <div class="metric-card__value">${ob.P2 || 0}</div>
                <div class="metric-card__label">P2 Open</div>
            </div>
            <div class="metric-card metric-card--p3">
                <div class="metric-card__value">${ob.P3 || 0}</div>
                <div class="metric-card__label">P3 Open</div>
            </div>
            <div class="metric-card metric-card--p4">
                <div class="metric-card__value">${ob.P4 || 0}</div>
                <div class="metric-card__label">P4 Open</div>
            </div>
            <div class="metric-card metric-card--sla ${(_metrics.sla_breached || 0) > 0 ? 'metric-card--alert' : ''}">
                <div class="metric-card__value">${_metrics.sla_breached || 0}</div>
                <div class="metric-card__label">SLA Breached</div>
            </div>
            <div class="metric-card">
                <div class="metric-card__value">${_metrics.avg_resolution_hours || 0}h</div>
                <div class="metric-card__label">Avg Resolution</div>
            </div>
            <div class="metric-card">
                <div class="metric-card__value">${_metrics.resolved_this_week || 0}</div>
                <div class="metric-card__label">Resolved (7d)</div>
            </div>
            <div class="metric-card">
                <div class="metric-card__value">${_metrics.total_resolved || 0}</div>
                <div class="metric-card__label">Total Resolved</div>
            </div>
        </div>`;
    }

    function _renderIncidentRow(inc) {
        const slaBadge = slaIcon(inc);
        const sevClass = severityColor[inc.severity] || 'badge--gray';
        return `
        <tr data-incident-id="${inc.id}">
            <td><span class="code-badge">${inc.code || '#'}</span></td>
            <td class="incident-title" title="${inc.title}">${inc.title}</td>
            <td><span class="badge ${sevClass}">${inc.severity}</span></td>
            <td>${inc.affected_module || '—'}</td>
            <td>${inc.status}</td>
            <td>${slaBadge}</td>
            <td>${inc.assigned_to || inc.assigned_to_id || '—'}</td>
            <td>
                <button class="btn-icon" onclick="HypercareView.openIncident(${inc.id})" title="View / Edit">✏️</button>
                ${inc.status !== 'resolved' ? `<button class="btn-icon" onclick="HypercareView.quickResolve(${inc.id})" title="Resolve">✅</button>` : ''}
            </td>
        </tr>`;
    }

    function _renderCRRow(cr) {
        const canApprove = cr.status === 'pending_approval';
        return `
        <tr data-cr-id="${cr.id}">
            <td><span class="code-badge">${cr.cr_number}</span></td>
            <td>${cr.title}</td>
            <td>${cr.change_type}</td>
            <td><span class="badge ${severityColor[cr.priority] || 'badge--gray'}">${cr.priority}</span></td>
            <td>${cr.status}</td>
            <td>
                ${canApprove
                    ? `<button class="btn btn--xs btn--success" onclick="HypercareView.approveCR(${cr.id})">Approve</button>
                       <button class="btn btn--xs btn--danger" onclick="HypercareView.rejectCR(${cr.id})">Reject</button>`
                    : '—'}
            </td>
        </tr>`;
    }

    function _renderHTML() {
        const incRows = _incidents.map(_renderIncidentRow).join('') ||
            '<tr><td colspan="8" class="empty-state">No incidents found.</td></tr>';
        const crRows = _changeRequests.map(_renderCRRow).join('') ||
            '<tr><td colspan="6" class="empty-state">No change requests found.</td></tr>';

        return `
        <div class="hypercare-view">
            <div class="view-header">
                <h2>⚡ Hypercare War Room</h2>
                <div class="view-header__actions">
                    <button class="btn btn--primary" onclick="HypercareView.showCreateIncident()">
                        + New Incident
                    </button>
                    <button class="btn btn--secondary" onclick="HypercareView.showCreateCR()">
                        + Change Request
                    </button>
                    <button class="btn btn--ghost" onclick="HypercareView.refresh()">↺ Refresh</button>
                </div>
            </div>

            ${_renderMetricsCards()}

            <!-- Incident Table -->
            <section class="view-section">
                <div class="section-header">
                    <h3>Incidents</h3>
                    <div class="section-filters">
                        <select onchange="HypercareView.filterStatus(this.value)">
                            <option value="">All statuses</option>
                            <option value="open">Open</option>
                            <option value="in_progress">In Progress</option>
                            <option value="resolved">Resolved</option>
                        </select>
                        <select onchange="HypercareView.filterSeverity(this.value)">
                            <option value="">All severities</option>
                            <option value="P1">P1</option>
                            <option value="P2">P2</option>
                            <option value="P3">P3</option>
                            <option value="P4">P4</option>
                        </select>
                    </div>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Code</th><th>Title</th><th>Severity</th>
                            <th>Module</th><th>Status</th><th>SLA</th>
                            <th>Assigned</th><th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="incident-tbody">${incRows}</tbody>
                </table>
            </section>

            <!-- Change Requests Table -->
            <section class="view-section">
                <h3>Change Requests</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>CR#</th><th>Title</th><th>Type</th>
                            <th>Priority</th><th>Status</th><th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="cr-tbody">${crRows}</tbody>
                </table>
            </section>

            <!-- Create/Edit Incident Modal (hidden by default) -->
            <div id="hypercare-modal" class="modal" style="display:none">
                <div class="modal__overlay" onclick="HypercareView.closeModal()"></div>
                <div class="modal__content" id="hypercare-modal-content"></div>
            </div>
        </div>`;
    }

    // ── Public API ────────────────────────────────────────────────────────────

    async function render(container) {
        _container = container;
        if (!container) { console.error('[HypercareView] container is null'); return; }

        container.innerHTML = '<div class="loading-spinner">Loading Hypercare dashboard…</div>';

        const program = App.getActiveProgram ? App.getActiveProgram() : null;
        if (!program) {
            container.innerHTML = '<div class="empty-state">Please select a program first.</div>';
            return;
        }

        _planId = await _resolveActivePlan(program.id);
        if (!_planId) {
            container.innerHTML = `
                <div class="empty-state">
                    No cutover plan found for this program.
                    Create a Cutover Plan in the Cutover module first.
                </div>`;
            return;
        }

        await Promise.all([_loadMetrics(), _loadIncidents(), _loadChangeRequests()]);
        container.innerHTML = _renderHTML();
    }

    async function refresh() {
        if (!_container || !_planId) return;
        await Promise.all([_loadMetrics(), _loadIncidents(), _loadChangeRequests()]);
        _container.innerHTML = _renderHTML();
    }

    function filterStatus(value) {
        _statusFilter = value;
        refresh();
    }

    function filterSeverity(value) {
        _severityFilter = value;
        refresh();
    }

    function closeModal() {
        const modal = document.getElementById('hypercare-modal');
        if (modal) modal.style.display = 'none';
    }

    function showCreateIncident() {
        const modal = document.getElementById('hypercare-modal');
        const content = document.getElementById('hypercare-modal-content');
        if (!modal || !content) return;

        content.innerHTML = `
        <div class="modal__header">
            <h3>New Incident</h3>
            <button class="modal__close" onclick="HypercareView.closeModal()">✕</button>
        </div>
        <form id="incident-form">
            <div class="form-group">
                <label>Title *</label>
                <input id="inc-title" type="text" maxlength="255" required placeholder="Short incident summary" />
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Severity</label>
                    <select id="inc-severity">
                        <option value="P3">P3 (Normal)</option>
                        <option value="P1">P1 (Critical)</option>
                        <option value="P2">P2 (High)</option>
                        <option value="P4">P4 (Low)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>SAP Module</label>
                    <input id="inc-module" type="text" maxlength="20" placeholder="FI, MM, SD…" />
                </div>
            </div>
            <div class="form-group">
                <label>Incident Type</label>
                <select id="inc-type">
                    <option value="">—</option>
                    <option value="system_down">System Down</option>
                    <option value="data_issue">Data Issue</option>
                    <option value="performance">Performance</option>
                    <option value="authorization">Authorization</option>
                    <option value="interface">Interface</option>
                    <option value="other">Other</option>
                </select>
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea id="inc-desc" rows="3" placeholder="Impact, steps to reproduce…"></textarea>
            </div>
            <div class="form-group">
                <label>Reported By</label>
                <input id="inc-reporter" type="text" maxlength="255" />
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn--primary" onclick="HypercareView._submitCreateIncident()">Create</button>
                <button type="button" class="btn btn--ghost" onclick="HypercareView.closeModal()">Cancel</button>
            </div>
        </form>`;
        modal.style.display = 'flex';
    }

    async function _submitCreateIncident() {
        const title = document.getElementById('inc-title').value.trim();
        if (!title) { toast('Title is required', 'error'); return; }

        const payload = {
            title,
            severity: document.getElementById('inc-severity').value,
            affected_module: document.getElementById('inc-module').value.trim() || null,
            incident_type: document.getElementById('inc-type').value || null,
            description: document.getElementById('inc-desc').value.trim(),
            reported_by: document.getElementById('inc-reporter').value.trim(),
        };

        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents`,
            { method: 'POST', body: JSON.stringify(payload) }
        );
        if (ok) {
            toast('Incident created', 'success');
            closeModal();
            refresh();
        } else {
            toast(data.error || 'Failed to create incident', 'error');
        }
    }

    async function openIncident(incidentId) {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}`
        );
        if (!ok) { toast(data.error || 'Not found', 'error'); return; }

        const inc = data;
        const modal = document.getElementById('hypercare-modal');
        const content = document.getElementById('hypercare-modal-content');

        content.innerHTML = `
        <div class="modal__header">
            <h3>${inc.code} — ${inc.title}</h3>
            <button class="modal__close" onclick="HypercareView.closeModal()">✕</button>
        </div>
        <div class="incident-detail">
            <div class="detail-row">
                <span class="badge ${severityColor[inc.severity] || ''}">${inc.severity}</span>
                <span>${inc.status}</span>
                <span>${slaIcon(inc)} SLA</span>
            </div>
            <p>${inc.description || '—'}</p>
            ${inc.sla_response_deadline ? `<p>Response deadline: ${new Date(inc.sla_response_deadline).toLocaleString()}</p>` : ''}
            ${inc.sla_resolution_deadline ? `<p>Resolution deadline: ${new Date(inc.sla_resolution_deadline).toLocaleString()}</p>` : ''}
        </div>
        <div class="incident-actions">
            ${!inc.first_response_at && inc.status !== 'resolved'
                ? `<button class="btn btn--secondary btn--sm" onclick="HypercareView._firstResponse(${inc.id})">Record 1st Response</button>`
                : ''}
            ${inc.status !== 'resolved'
                ? `<button class="btn btn--success btn--sm" onclick="HypercareView.quickResolve(${inc.id})">Resolve</button>`
                : ''}
        </div>`;
        modal.style.display = 'flex';
    }

    async function _firstResponse(incidentId) {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}/first-response`,
            { method: 'POST' }
        );
        if (ok) { toast('First response recorded', 'success'); closeModal(); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    async function quickResolve(incidentId) {
        const resolution = window.prompt('Resolution summary:');
        if (!resolution) return;
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}/resolve`,
            { method: 'POST', body: JSON.stringify({ resolution }) }
        );
        if (ok) { toast('Incident resolved ✅', 'success'); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    function showCreateCR() {
        const modal = document.getElementById('hypercare-modal');
        const content = document.getElementById('hypercare-modal-content');
        if (!modal || !content) return;

        content.innerHTML = `
        <div class="modal__header">
            <h3>New Change Request</h3>
            <button class="modal__close" onclick="HypercareView.closeModal()">✕</button>
        </div>
        <form id="cr-form">
            <div class="form-group">
                <label>Title *</label>
                <input id="cr-title" type="text" maxlength="255" required />
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Change Type *</label>
                    <select id="cr-type">
                        <option value="config">Config</option>
                        <option value="development">Development</option>
                        <option value="data">Data</option>
                        <option value="authorization">Authorization</option>
                        <option value="emergency">Emergency</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Priority</label>
                    <select id="cr-priority">
                        <option value="P3">P3 (Normal)</option>
                        <option value="P1">P1 (Critical)</option>
                        <option value="P2">P2 (High)</option>
                        <option value="P4">P4 (Low)</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Impact Assessment</label>
                <textarea id="cr-impact" rows="3"></textarea>
            </div>
            <div class="form-group">
                <label>Rollback Plan</label>
                <textarea id="cr-rollback" rows="2"></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn--primary" onclick="HypercareView._submitCreateCR()">Submit</button>
                <button type="button" class="btn btn--ghost" onclick="HypercareView.closeModal()">Cancel</button>
            </div>
        </form>`;
        modal.style.display = 'flex';
    }

    async function _submitCreateCR() {
        const title = document.getElementById('cr-title').value.trim();
        if (!title) { toast('Title is required', 'error'); return; }

        const payload = {
            title,
            change_type: document.getElementById('cr-type').value,
            priority: document.getElementById('cr-priority').value,
            impact_assessment: document.getElementById('cr-impact').value.trim(),
            rollback_plan: document.getElementById('cr-rollback').value.trim(),
        };

        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/change-requests`,
            { method: 'POST', body: JSON.stringify(payload) }
        );
        if (ok) {
            toast(`CR ${data.cr_number} created`, 'success');
            closeModal();
            refresh();
        } else {
            toast(data.error || 'Failed', 'error');
        }
    }

    async function approveCR(crId) {
        if (!window.confirm('Approve this change request?')) return;
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/change-requests/${crId}/approve`,
            { method: 'POST' }
        );
        if (ok) { toast('CR approved ✅', 'success'); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    async function rejectCR(crId) {
        const reason = window.prompt('Rejection reason:');
        if (reason === null) return;  // cancelled
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/change-requests/${crId}/reject`,
            { method: 'POST', body: JSON.stringify({ rejection_reason: reason }) }
        );
        if (ok) { toast('CR rejected', 'info'); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    // ── Expose ─────────────────────────────────────────────────────────────────
    return {
        render,
        refresh,
        filterStatus,
        filterSeverity,
        closeModal,
        showCreateIncident,
        _submitCreateIncident,
        openIncident,
        _firstResponse,
        quickResolve,
        showCreateCR,
        _submitCreateCR,
        approveCR,
        rejectCR,
    };
})();
