/**
 * Hypercare War Room Dashboard — FDD-B03 (MVP) + Phase-2 + Phase-3.
 *
 * Provides:
 *  - Go-Live timer, hypercare phase, system health RAG indicator
 *  - P1/P2/P3/P4 open incident priority cards (hc-kpi-grid)
 *  - SLA breach counter
 *  - Escalation alerts panel (unacknowledged events)
 *  - War Room overview widget (per-war-room analytics)
 *  - Tab-based views: Incidents | Change Requests | War Rooms
 *  - Modal create screens via App.openModal() / App.closeModal()
 *  - War Room CRUD with incident/CR assignment
 *  - Comment thread panel
 *  - Exit readiness widget with sign-off button
 *  - 30-second P1/P2 live feed polling
 *
 * Dependencies:
 *  - App.getActiveProgram()  -> { id, name }
 *  - App.openModal(html), App.closeModal()
 *  - GET /api/v1/run-sustain/plans/:planId/hypercare/war-room
 *  - GET /api/v1/run-sustain/plans/:planId/hypercare/incidents
 *  - POST/PUT endpoints per hypercare_bp
 */

const HypercareView = (() => {
    // -- State ---------------------------------------------------------------
    let _planId = null;
    let _incidents = [];
    let _changeRequests = [];
    let _warRooms = [];
    let _warRoomAnalytics = [];
    let _metrics = {};
    let _warRoom = {};
    let _exitCriteria = [];
    let _container = null;
    let _statusFilter = '';
    let _severityFilter = '';
    let _currentTab = 'incidents';
    let _pollTimer = null;

    // -- Helpers -------------------------------------------------------------

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

    const healthRAG = { green: '#22c55e', yellow: '#eab308', red: '#ef4444' };

    const slaIcon = (inc) => {
        if (inc.sla_resolution_breached) return '<span style="color:#ef4444">&#9679;</span>';
        if (inc.sla_response_breached) return '<span style="color:#eab308">&#9679;</span>';
        return '<span style="color:#22c55e">&#9679;</span>';
    };

    function _timeAgo(isoStr) {
        if (!isoStr) return '';
        const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
        if (diff < 60) return 'just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    function toast(msg, type = 'info') {
        if (window.Toast) { window.Toast[type](msg); }
    }

    // -- Data Fetching -------------------------------------------------------

    async function _loadWarRoom() {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/war-room`
        );
        if (ok) {
            _warRoom = data;
            _metrics = data.metrics || {};
        }
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

    async function _loadExitCriteria() {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/exit-criteria`
        );
        if (ok) _exitCriteria = data.items || [];
    }

    async function _loadWarRooms() {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/war-rooms`
        );
        if (ok) _warRooms = data.items || [];
    }

    async function _loadWarRoomAnalytics() {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/war-room-analytics`
        );
        if (ok) _warRoomAnalytics = data.war_rooms || [];
    }

    async function _resolveActivePlan(programId) {
        const { ok, data } = await API(
            `/api/v1/cutover/plans?program_id=${programId}`
        );
        if (!ok || !data.items || data.items.length === 0) return null;
        return data.items[0].id;
    }

    // -- Rendering: Dashboard Header -----------------------------------------

    function _renderWarRoomHeader() {
        const wr = _warRoom;
        const health = wr.system_health || 'green';
        const healthColor = healthRAG[health] || healthRAG.green;
        const goLiveDays = wr.go_live_plus_days;
        const phase = wr.hypercare_phase || 'Hypercare Active';
        const remaining = wr.hypercare_remaining_days;
        const exitPct = wr.exit_readiness_pct || 0;

        return `
        <div class="hc-status-bar" style="--hc-health-color:${healthColor}">
            <span class="hc-status-bar__health" title="System Health: ${health.toUpperCase()}"></span>
            <span class="hc-status-bar__phase">${phase}</span>
            ${goLiveDays !== null && goLiveDays !== undefined
                ? `<span class="hc-status-bar__badge">Go-Live +${goLiveDays}d</span>`
                : ''}
            <span class="hc-status-bar__meta">
                ${remaining !== null && remaining !== undefined
                    ? `<span>${remaining}d remaining</span>`
                    : ''}
                <span>Exit: <strong>${exitPct}%</strong></span>
            </span>
        </div>`;
    }

    function _renderMetricsCards() {
        const ob = _metrics.open_by_priority || {};
        const p1 = ob.P1 || 0;
        const p2 = ob.P2 || 0;
        const slaBreach = _metrics.sla_breached || 0;
        const resolved = _metrics.total_resolved || 0;

        return `
        <div class="hc-kpi-grid">
            <div class="hc-kpi hc-kpi--p1">
                <div class="hc-kpi__value ${p1 > 0 ? 'hc-kpi__value--red' : ''}">${p1}</div>
                <div class="hc-kpi__label">P1 Critical</div>
            </div>
            <div class="hc-kpi hc-kpi--p2">
                <div class="hc-kpi__value ${p2 > 0 ? 'hc-kpi__value--orange' : ''}">${p2}</div>
                <div class="hc-kpi__label">P2 High</div>
            </div>
            <div class="hc-kpi hc-kpi--p3">
                <div class="hc-kpi__value">${ob.P3 || 0}</div>
                <div class="hc-kpi__label">P3 Medium</div>
            </div>
            <div class="hc-kpi hc-kpi--p4">
                <div class="hc-kpi__value">${ob.P4 || 0}</div>
                <div class="hc-kpi__label">P4 Low</div>
            </div>
            <div class="hc-kpi ${slaBreach > 0 ? 'hc-kpi--sla-alert' : ''}">
                <div class="hc-kpi__value ${slaBreach > 0 ? 'hc-kpi__value--red' : ''}">${slaBreach}</div>
                <div class="hc-kpi__label">SLA Breached</div>
            </div>
            <div class="hc-kpi">
                <div class="hc-kpi__value">${_metrics.avg_resolution_hours || 0}h</div>
                <div class="hc-kpi__label">Avg Resolution</div>
            </div>
            <div class="hc-kpi">
                <div class="hc-kpi__value">${_metrics.resolved_this_week || 0}</div>
                <div class="hc-kpi__label">Resolved (7d)</div>
            </div>
            <div class="hc-kpi">
                <div class="hc-kpi__value ${resolved > 0 ? 'hc-kpi__value--green' : ''}">${resolved}</div>
                <div class="hc-kpi__label">Total Resolved</div>
            </div>
        </div>`;
    }

    function _renderEscalationAlerts() {
        const alerts = (_warRoom.active_escalations || []).slice(0, 5);
        if (alerts.length === 0) return '';

        const rows = alerts.map(e => {
            const isCritical = ['L3', 'vendor', 'management'].includes(e.escalation_level);
            return `
            <div class="hc-esc-alert ${isCritical ? 'hc-esc-alert--critical' : ''}">
                <span class="badge badge--${isCritical ? 'red' : 'orange'}" style="font-size:0.75em;">${e.escalation_level}</span>
                <span style="flex:1;">${e.escalated_to || 'Unknown'} &mdash; ${e.trigger_type || ''}</span>
                <span style="font-size:0.8em;color:var(--sap-text-secondary,#6a6d70);">${_timeAgo(e.created_at)}</span>
                <button class="btn btn--xs btn--ghost" onclick="HypercareView.acknowledgeEscalation(${e.id})">Ack</button>
            </div>`;
        }).join('');

        return `
        <div class="hc-esc-panel">
            <div class="hc-esc-panel__header">
                Escalation Alerts
                <span class="badge badge--red" style="font-size:0.75em;">${alerts.length}</span>
            </div>
            ${rows}
        </div>`;
    }

    // -- Rendering: War Room Overview Widget ----------------------------------

    function _renderWarRoomOverview() {
        if (_warRoomAnalytics.length === 0) return '';

        const activeRooms = _warRoomAnalytics.filter(wr => wr.status !== 'closed');
        if (activeRooms.length === 0) return '';

        const rows = activeRooms.map(wr => {
            const hasP1 = wr.open_p1 > 0;
            const hasP2 = wr.open_p2 > 0;
            const borderClass = hasP1 ? 'hc-wr-row--p1' : hasP2 ? 'hc-wr-row--p2' : '';
            return `
            <div class="hc-wr-row ${borderClass}" onclick="HypercareView.switchTab('war-rooms')">
                <span class="code-badge">${wr.code || '#'}</span>
                <span class="hc-wr-row__name">${wr.name}</span>
                <span class="badge badge--${wr.status === 'active' ? 'blue' : 'gray'}" style="font-size:0.75em;">${wr.status}</span>
                <span class="hc-wr-row__stats">
                    ${wr.open_incidents} open${hasP1 ? ` <span style="color:#dc2626">(${wr.open_p1} P1)</span>` : ''}${hasP2 ? ` <span style="color:#e76500">(${wr.open_p2} P2)</span>` : ''}
                </span>
                ${wr.cr_count > 0 ? `<span style="font-size:0.85em;color:var(--sap-text-secondary)">${wr.cr_count} CRs</span>` : ''}
            </div>`;
        }).join('');

        return `
        <div class="hc-wr-overview">
            <div style="font-size:13px;font-weight:600;color:var(--sap-text-secondary,#64748b);margin-bottom:8px;">Active War Rooms</div>
            ${rows}
        </div>`;
    }

    // -- Rendering: Tab Content -----------------------------------------------

    function _renderIncidentRow(inc) {
        const slaBadge = slaIcon(inc);
        const sevClass = severityColor[inc.severity] || 'badge--gray';
        const escLevel = inc.current_escalation_level
            ? `<span class="badge badge--red" style="font-size:0.7em;margin-left:4px;">${inc.current_escalation_level}</span>`
            : '';
        const wrBadge = inc.war_room_id
            ? `<span class="badge badge--blue" style="font-size:0.7em;margin-left:4px;">WR</span>`
            : '';
        return `
        <tr data-incident-id="${inc.id}">
            <td><span class="code-badge">${inc.code || '#'}</span></td>
            <td class="incident-title" title="${inc.title}">${inc.title}${escLevel}${wrBadge}</td>
            <td><span class="badge ${sevClass}">${inc.severity}</span></td>
            <td>${inc.affected_module || '\u2014'}</td>
            <td>${inc.status}</td>
            <td>${slaBadge}</td>
            <td>${inc.assigned_to || inc.assigned_to_id || '\u2014'}</td>
            <td>
                <button class="btn-icon" onclick="HypercareView.openIncident(${inc.id})" title="View / Edit">&#9998;</button>
                ${inc.status !== 'resolved' && inc.status !== 'closed'
                    ? `<button class="btn-icon" onclick="HypercareView.quickResolve(${inc.id})" title="Resolve">&#10004;</button>`
                    : ''}
            </td>
        </tr>`;
    }

    function _renderIncidentTab() {
        const incRows = _incidents.map(_renderIncidentRow).join('') ||
            '<tr><td colspan="8" class="empty-state">No incidents found.</td></tr>';

        return `
        <div class="section-header" style="margin-bottom:12px;">
            <div class="section-filters">
                <select onchange="HypercareView.filterStatus(this.value)">
                    <option value="">All statuses</option>
                    <option value="open" ${_statusFilter === 'open' ? 'selected' : ''}>Open</option>
                    <option value="investigating" ${_statusFilter === 'investigating' ? 'selected' : ''}>Investigating</option>
                    <option value="resolved" ${_statusFilter === 'resolved' ? 'selected' : ''}>Resolved</option>
                    <option value="closed" ${_statusFilter === 'closed' ? 'selected' : ''}>Closed</option>
                </select>
                <select onchange="HypercareView.filterSeverity(this.value)">
                    <option value="">All severities</option>
                    <option value="P1" ${_severityFilter === 'P1' ? 'selected' : ''}>P1</option>
                    <option value="P2" ${_severityFilter === 'P2' ? 'selected' : ''}>P2</option>
                    <option value="P3" ${_severityFilter === 'P3' ? 'selected' : ''}>P3</option>
                    <option value="P4" ${_severityFilter === 'P4' ? 'selected' : ''}>P4</option>
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
        </table>`;
    }

    function _renderCRRow(cr) {
        const canApprove = cr.status === 'pending_approval';
        const wrBadge = cr.war_room_id
            ? `<span class="badge badge--blue" style="font-size:0.7em;margin-left:4px;">WR</span>`
            : '';
        return `
        <tr data-cr-id="${cr.id}">
            <td><span class="code-badge">${cr.cr_number}</span></td>
            <td>${cr.title}${wrBadge}</td>
            <td>${cr.change_type}</td>
            <td><span class="badge ${severityColor[cr.priority] || 'badge--gray'}">${cr.priority}</span></td>
            <td>${cr.status}</td>
            <td>
                ${canApprove
                    ? `<button class="btn btn--xs btn--success" onclick="HypercareView.approveCR(${cr.id})">Approve</button>
                       <button class="btn btn--xs btn--danger" onclick="HypercareView.rejectCR(${cr.id})">Reject</button>`
                    : '\u2014'}
            </td>
        </tr>`;
    }

    function _renderCRTab() {
        const crRows = _changeRequests.map(_renderCRRow).join('') ||
            '<tr><td colspan="6" class="empty-state">No change requests found.</td></tr>';

        return `
        <table class="data-table">
            <thead>
                <tr>
                    <th>CR#</th><th>Title</th><th>Type</th>
                    <th>Priority</th><th>Status</th><th>Actions</th>
                </tr>
            </thead>
            <tbody id="cr-tbody">${crRows}</tbody>
        </table>`;
    }

    function _renderWarRoomsTab() {
        if (_warRooms.length === 0) {
            return `
            <div style="padding:24px;text-align:center;color:var(--sap-text-secondary,#6a6d70);">
                No war rooms created yet.
                <button class="btn btn--xs btn--primary" onclick="HypercareView.showCreateWarRoom()" style="margin-left:8px;">
                    + Create War Room
                </button>
            </div>`;
        }

        const cards = _warRooms.map(wr => {
            const hasP1 = (wr.open_incident_count || 0) > 0;
            const statusBadgeClass = wr.status === 'active' ? 'badge--blue'
                : wr.status === 'monitoring' ? 'badge--yellow'
                : wr.status === 'resolved' ? 'badge--green'
                : 'badge--gray';
            const priorityClass = severityColor[wr.priority] || 'badge--gray';

            return `
            <div class="hc-wr-card" onclick="HypercareView.openWarRoom(${wr.id})">
                <div class="hc-wr-card__header">
                    <span class="code-badge">${wr.code || '#'}</span>
                    <span class="hc-wr-card__name">${wr.name}</span>
                    <span class="badge ${statusBadgeClass}" style="font-size:0.75em;">${wr.status}</span>
                </div>
                <div class="hc-wr-card__body">
                    <span class="badge ${priorityClass}" style="font-size:0.75em;">${wr.priority}</span>
                    ${wr.affected_module ? `<span style="font-size:0.85em;color:var(--sap-text-secondary)">${wr.affected_module}</span>` : ''}
                    ${wr.war_room_lead ? `<span style="font-size:0.85em;color:var(--sap-text-secondary)">Lead: ${wr.war_room_lead}</span>` : ''}
                </div>
                <div class="hc-wr-card__footer">
                    <span>${wr.incident_count || 0} incidents</span>
                    <span>${wr.open_incident_count || 0} open</span>
                    <span>${wr.cr_count || 0} CRs</span>
                </div>
            </div>`;
        }).join('');

        return `
        <div style="margin-bottom:12px;">
            <button class="btn btn--primary btn--sm" onclick="HypercareView.showCreateWarRoom()">+ Create War Room</button>
        </div>
        <div class="hc-wr-grid">${cards}</div>`;
    }

    function _renderTabContent(tab) {
        const el = document.getElementById('hc-tab-content');
        if (!el) return;

        if (tab === 'incidents') {
            el.innerHTML = _renderIncidentTab();
        } else if (tab === 'change-requests') {
            el.innerHTML = _renderCRTab();
        } else if (tab === 'war-rooms') {
            el.innerHTML = _renderWarRoomsTab();
        }
    }

    // -- Rendering: Exit Readiness -------------------------------------------

    function _renderExitReadiness() {
        if (_exitCriteria.length === 0) {
            return `
            <section class="view-section">
                <div class="section-header">
                    <h3>Exit Readiness</h3>
                </div>
                <div style="padding:24px;text-align:center;color:var(--sap-text-secondary,#6a6d70);">
                    No exit criteria defined.
                    <button class="btn btn--xs btn--secondary" onclick="HypercareView.seedExitCriteria()" style="margin-left:8px;">
                        Seed Standard Criteria
                    </button>
                </div>
            </section>`;
        }

        const met = _exitCriteria.filter(c => c.status === 'met').length;
        const total = _exitCriteria.length;
        const pct = total > 0 ? Math.round(met / total * 100) : 0;
        const pctColor = pct >= 80 ? '#16a34a' : pct >= 50 ? '#ca8a04' : '#dc2626';
        const allMandatoryMet = _exitCriteria
            .filter(c => c.is_mandatory)
            .every(c => c.status === 'met');

        const criteriaGrid = _exitCriteria.map(c => {
            let iconClass, iconChar;
            if (c.status === 'met') { iconClass = 'hc-exit-icon--met'; iconChar = '&#10003;'; }
            else if (c.status === 'partially_met') { iconClass = 'hc-exit-icon--partial'; iconChar = '&#9888;'; }
            else { iconClass = 'hc-exit-icon--not-met'; iconChar = '&#10007;'; }
            const mandatoryBadge = c.is_mandatory
                ? '<span style="font-size:0.7em;color:#dc2626;margin-left:4px;">*</span>' : '';
            return `
            <div class="hc-exit-item">
                <span class="hc-exit-icon ${iconClass}">${iconChar}</span>
                <span style="flex:1;">${c.name}${mandatoryBadge}</span>
                ${c.current_value !== null && c.current_value !== undefined
                    ? `<span style="font-size:0.8em;color:var(--sap-text-secondary,#6a6d70);">${c.current_value}</span>` : ''}
            </div>`;
        }).join('');

        return `
        <section class="view-section">
            <div class="hc-exit-header">
                <div class="hc-exit-header__left">
                    <h3 style="margin:0;">Exit Readiness</h3>
                    <span class="hc-status-bar__badge" style="color:${pctColor}">${pct}%</span>
                </div>
                <div class="hc-exit-header__actions">
                    <button class="btn btn--xs btn--ghost" onclick="HypercareView.evaluateExitCriteria()">Re-evaluate</button>
                    <button class="btn btn--xs btn--primary" onclick="HypercareView.requestExitSignoff()"
                        ${allMandatoryMet ? '' : 'disabled title="All mandatory criteria must be met"'}>
                        Request Exit Sign-off
                    </button>
                </div>
            </div>
            <div class="hc-exit-progress">
                <div class="hc-exit-progress__bar" style="background:${pctColor};width:${pct}%;"></div>
            </div>
            <div class="hc-exit-grid">
                ${criteriaGrid}
            </div>
            <div style="margin-top:8px;font-size:12px;color:var(--sap-text-secondary,#6a6d70);">* = mandatory for exit</div>
        </section>`;
    }

    // -- Main Rendering ------------------------------------------------------

    function _renderHTML() {
        const incCount = _incidents.length;
        const crCount = _changeRequests.length;
        const wrCount = _warRooms.length;

        return `
        <div class="hc-war-room">
            <div class="pg-view-header" style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
                <h2>Hypercare War Room</h2>
                <div style="display:flex;gap:8px;flex-wrap:wrap">
                    <button class="btn btn--primary" onclick="HypercareView.showCreateIncident()">
                        + New Incident
                    </button>
                    <button class="btn btn--secondary" onclick="HypercareView.showCreateCR()">
                        + Change Request
                    </button>
                    <button class="btn btn--ghost" onclick="HypercareView.seedEscalationRules()">
                        Setup Escalation
                    </button>
                    <button class="btn btn--ghost" onclick="HypercareView.refresh()">Refresh</button>
                </div>
            </div>

            ${_renderWarRoomHeader()}
            ${_renderMetricsCards()}
            ${_renderEscalationAlerts()}
            ${_renderWarRoomOverview()}

            <!-- Tabs: Incidents | Change Requests | War Rooms -->
            <div class="tabs" style="margin-bottom:12px">
                <button class="tab-btn ${_currentTab === 'incidents' ? 'active' : ''}" data-tab="incidents" onclick="HypercareView.switchTab('incidents')">
                    Incidents <span class="badge badge--sm">${incCount}</span>
                </button>
                <button class="tab-btn ${_currentTab === 'change-requests' ? 'active' : ''}" data-tab="change-requests" onclick="HypercareView.switchTab('change-requests')">
                    Change Requests <span class="badge badge--sm">${crCount}</span>
                </button>
                <button class="tab-btn ${_currentTab === 'war-rooms' ? 'active' : ''}" data-tab="war-rooms" onclick="HypercareView.switchTab('war-rooms')">
                    War Rooms <span class="badge badge--sm">${wrCount}</span>
                </button>
            </div>
            <div id="hc-tab-content"></div>

            <!-- Exit Readiness -->
            ${_renderExitReadiness()}
        </div>`;
    }

    // -- Public API ----------------------------------------------------------

    async function render(container) {
        _container = container;
        if (!container) { console.error('[HypercareView] container is null'); return; }

        container.innerHTML = '<div class="loading-spinner">Loading Hypercare dashboard\u2026</div>';

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

        await Promise.all([
            _loadWarRoom(), _loadIncidents(), _loadChangeRequests(),
            _loadExitCriteria(), _loadWarRooms(), _loadWarRoomAnalytics(),
        ]);
        container.innerHTML = _renderHTML();
        _renderTabContent(_currentTab);
        _startPolling();
    }

    async function refresh() {
        if (!_container || !_planId) return;
        await Promise.all([
            _loadWarRoom(), _loadIncidents(), _loadChangeRequests(),
            _loadExitCriteria(), _loadWarRooms(), _loadWarRoomAnalytics(),
        ]);
        _container.innerHTML = _renderHTML();
        _renderTabContent(_currentTab);
    }

    // -- Tab Switching -------------------------------------------------------

    function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('.tabs .tab-btn').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        _renderTabContent(tab);
    }

    // -- 30s P1/P2 Live Feed Polling -----------------------------------------

    function _startPolling() {
        _stopPolling();
        _pollTimer = setInterval(async () => {
            if (!_planId) return;
            const { ok, data } = await API(
                `/api/v1/run-sustain/plans/${_planId}/hypercare/war-room`
            );
            if (!ok) return;

            _warRoom = data;
            _metrics = data.metrics || {};

            const statusBar = document.querySelector('.hc-status-bar');
            if (statusBar) {
                statusBar.outerHTML = _renderWarRoomHeader();
            }

            const newAlertCount = (data.active_escalations || []).length;
            const currentAlertBadge = document.querySelector('.hc-esc-panel__header .badge.badge--red');
            const currentCount = currentAlertBadge ? parseInt(currentAlertBadge.textContent) : 0;
            if (newAlertCount !== currentCount) {
                refresh();
            }
        }, 30000);
    }

    function _stopPolling() {
        if (_pollTimer) {
            clearInterval(_pollTimer);
            _pollTimer = null;
        }
    }

    function filterStatus(value) {
        _statusFilter = value;
        _loadIncidents().then(() => _renderTabContent('incidents'));
    }

    function filterSeverity(value) {
        _severityFilter = value;
        _loadIncidents().then(() => _renderTabContent('incidents'));
    }

    // -- Incident CRUD (Modals via App.openModal) ----------------------------

    function showCreateIncident() {
        const html = `<div class="modal">
            <div class="modal__header">
                <h3>New Incident</h3>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal__body">
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
                            <input id="inc-module" type="text" maxlength="20" placeholder="FI, MM, SD\u2026" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Incident Type</label>
                        <select id="inc-type">
                            <option value="">\u2014</option>
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
                        <textarea id="inc-desc" rows="3" placeholder="Impact, steps to reproduce\u2026"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Reported By</label>
                        <input id="inc-reporter" type="text" maxlength="255" />
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn--primary" onclick="HypercareView._submitCreateIncident()">Create</button>
                        <button type="button" class="btn btn--ghost" onclick="App.closeModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>`;
        App.openModal(html);
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
            App.closeModal();
            refresh();
        } else {
            toast(data.error || 'Failed to create incident', 'error');
        }
    }

    async function openIncident(incidentId) {
        const [incRes, escRes, lessonsRes] = await Promise.all([
            API(`/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}`),
            API(`/api/v1/run-sustain/plans/${_planId}/hypercare/escalations?incident_id=${incidentId}`),
            API(`/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}/similar-lessons?max_results=3`),
        ]);
        if (!incRes.ok) { toast(incRes.data.error || 'Not found', 'error'); return; }

        const inc = incRes.data;
        const escalations = escRes.ok ? (escRes.data.items || []) : [];
        const lessons = lessonsRes.ok ? (lessonsRes.data.items || []) : [];
        const isOpen = !['resolved', 'closed'].includes(inc.status);

        // War room assignment options
        const activeWRs = _warRooms.filter(wr => wr.status !== 'closed');
        const wrOptions = activeWRs.map(wr =>
            `<option value="${wr.id}" ${inc.war_room_id === wr.id ? 'selected' : ''}>${wr.code} - ${wr.name}</option>`
        ).join('');
        const wrSelect = activeWRs.length > 0
            ? `<div style="margin:8px 0;">
                <label style="font-size:0.85em;font-weight:600;">Assign to War Room</label>
                <select onchange="HypercareView._assignIncidentWarRoom(${inc.id}, this.value)" style="margin-left:8px;">
                    <option value="">-- None --</option>
                    ${wrOptions}
                </select>
               </div>`
            : '';

        const escHTML = escalations.length > 0
            ? `<div style="margin-top:12px;">
                <h4 style="margin-bottom:6px;">Escalation History</h4>
                ${escalations.map(e => `
                    <div style="display:flex;gap:8px;padding:4px 0;font-size:0.9em;border-bottom:1px solid #f1f5f9;">
                        <span class="badge badge--${['L3','vendor','management'].includes(e.escalation_level) ? 'red' : 'orange'}" style="font-size:0.75em;">${e.escalation_level}</span>
                        <span>${e.escalated_to || ''}</span>
                        <span style="color:#94a3b8;margin-left:auto;">${_timeAgo(e.created_at)}</span>
                        ${e.acknowledged_at ? '<span style="color:#22c55e;">Ack</span>' : ''}
                    </div>`).join('')}
               </div>`
            : '';

        const lessonsHTML = lessons.length > 0
            ? `<div style="margin-top:12px;">
                <h4 style="margin-bottom:6px;">Similar Lessons</h4>
                ${lessons.map(l => `
                    <div style="padding:4px 0;font-size:0.9em;border-bottom:1px solid #f1f5f9;">
                        ${l.title || 'Untitled'} <span style="color:#94a3b8;">${l.category || ''}</span>
                    </div>`).join('')}
               </div>`
            : '';

        const html = `<div class="modal">
            <div class="modal__header">
                <h3>${inc.code} \u2014 ${inc.title}</h3>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal__body">
                <div class="detail-row" style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
                    <span class="badge ${severityColor[inc.severity] || ''}">${inc.severity}</span>
                    <span>${inc.status}</span>
                    <span>${slaIcon(inc)} SLA</span>
                    ${inc.current_escalation_level
                        ? `<span class="badge badge--red" style="font-size:0.8em;">${inc.current_escalation_level}</span>`
                        : ''}
                </div>
                <p>${inc.description || '\u2014'}</p>
                ${inc.sla_response_deadline ? `<p style="font-size:0.9em;">Response deadline: ${new Date(inc.sla_response_deadline).toLocaleString()}</p>` : ''}
                ${inc.sla_resolution_deadline ? `<p style="font-size:0.9em;">Resolution deadline: ${new Date(inc.sla_resolution_deadline).toLocaleString()}</p>` : ''}
                ${inc.root_cause ? `<p style="font-size:0.9em;"><strong>Root Cause:</strong> ${inc.root_cause}</p>` : ''}
                ${wrSelect}
                <div class="incident-actions" style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;">
                    ${!inc.first_response_at && isOpen
                        ? `<button class="btn btn--secondary btn--sm" onclick="HypercareView._firstResponse(${inc.id})">Record 1st Response</button>`
                        : ''}
                    ${isOpen
                        ? `<button class="btn btn--success btn--sm" onclick="HypercareView.quickResolve(${inc.id})">Resolve</button>`
                        : ''}
                    ${isOpen
                        ? `<button class="btn btn--warning btn--sm" onclick="HypercareView.showEscalateModal(${inc.id})">Escalate</button>`
                        : ''}
                    ${!isOpen
                        ? `<button class="btn btn--secondary btn--sm" onclick="HypercareView.createLessonFromIncident(${inc.id})">Create Lesson</button>`
                        : ''}
                </div>
                ${escHTML}
                ${lessonsHTML}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function _firstResponse(incidentId) {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}/first-response`,
            { method: 'POST' }
        );
        if (ok) { toast('First response recorded', 'success'); App.closeModal(); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    async function quickResolve(incidentId) {
        const resolution = window.prompt('Resolution summary:');
        if (!resolution) return;
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}/resolve`,
            { method: 'POST', body: JSON.stringify({ resolution }) }
        );
        if (ok) { toast('Incident resolved', 'success'); App.closeModal(); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    async function _assignIncidentWarRoom(incidentId, warRoomId) {
        const payload = { war_room_id: warRoomId ? parseInt(warRoomId) : null };
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}/assign-war-room`,
            { method: 'POST', body: JSON.stringify(payload) }
        );
        if (ok) { toast('War room assignment updated', 'success'); }
        else toast(data.error || 'Failed', 'error');
    }

    // -- Escalation Actions --------------------------------------------------

    function showEscalateModal(incidentId) {
        const html = `<div class="modal">
            <div class="modal__header">
                <h3>Escalate Incident</h3>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal__body">
                <form>
                    <div class="form-group">
                        <label>Escalation Level *</label>
                        <select id="esc-level">
                            <option value="L1">L1 - Support Team</option>
                            <option value="L2">L2 - Functional Lead</option>
                            <option value="L3">L3 - Technical Expert</option>
                            <option value="vendor">Vendor - SAP Support</option>
                            <option value="management">Management</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Escalate To *</label>
                        <input id="esc-to" type="text" maxlength="150" placeholder="Person or team name" />
                    </div>
                    <div class="form-group">
                        <label>Notes</label>
                        <textarea id="esc-notes" rows="2" placeholder="Reason for escalation"></textarea>
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn--warning" onclick="HypercareView._submitEscalation(${incidentId})">Escalate</button>
                        <button type="button" class="btn btn--ghost" onclick="App.closeModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>`;
        App.openModal(html);
    }

    async function _submitEscalation(incidentId) {
        const escalated_to = document.getElementById('esc-to').value.trim();
        if (!escalated_to) { toast('Escalate To is required', 'error'); return; }

        const payload = {
            escalation_level: document.getElementById('esc-level').value,
            escalated_to,
            notes: document.getElementById('esc-notes').value.trim(),
        };

        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}/escalate`,
            { method: 'POST', body: JSON.stringify(payload) }
        );
        if (ok) { toast('Incident escalated', 'success'); App.closeModal(); refresh(); }
        else toast(data.error || 'Escalation failed', 'error');
    }

    async function acknowledgeEscalation(eventId) {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/escalations/${eventId}/acknowledge`,
            { method: 'POST' }
        );
        if (ok) { toast('Escalation acknowledged', 'success'); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    async function seedEscalationRules() {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/escalation-rules/seed`,
            { method: 'POST' }
        );
        if (ok) {
            const count = (data.items || []).length;
            toast(count > 0 ? `${count} escalation rules created` : 'Rules already exist', 'success');
        } else {
            toast(data.error || 'Failed', 'error');
        }
    }

    // -- Change Request CRUD -------------------------------------------------

    function showCreateCR() {
        const html = `<div class="modal">
            <div class="modal__header">
                <h3>New Change Request</h3>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal__body">
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
                        <button type="button" class="btn btn--ghost" onclick="App.closeModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>`;
        App.openModal(html);
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
            App.closeModal();
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
        if (ok) { toast('CR approved', 'success'); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    async function rejectCR(crId) {
        const reason = window.prompt('Rejection reason:');
        if (reason === null) return;
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/change-requests/${crId}/reject`,
            { method: 'POST', body: JSON.stringify({ rejection_reason: reason }) }
        );
        if (ok) { toast('CR rejected', 'info'); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    // -- War Room CRUD -------------------------------------------------------

    function showCreateWarRoom() {
        const html = `<div class="modal">
            <div class="modal__header">
                <h3>Create War Room</h3>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal__body">
                <form id="wr-form">
                    <div class="form-group">
                        <label>Name *</label>
                        <input id="wr-name" type="text" maxlength="255" required placeholder="e.g. MM Data Migration Issues" />
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Priority</label>
                            <select id="wr-priority">
                                <option value="P2">P2 (High)</option>
                                <option value="P1">P1 (Critical)</option>
                                <option value="P3">P3 (Normal)</option>
                                <option value="P4">P4 (Low)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>SAP Module</label>
                            <input id="wr-module" type="text" maxlength="20" placeholder="FI, MM, SD\u2026" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label>War Room Lead</label>
                        <input id="wr-lead" type="text" maxlength="100" placeholder="Person name" />
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="wr-desc" rows="3" placeholder="Context and scope of this war room\u2026"></textarea>
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn--primary" onclick="HypercareView._submitCreateWarRoom()">Create</button>
                        <button type="button" class="btn btn--ghost" onclick="App.closeModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>`;
        App.openModal(html);
    }

    async function _submitCreateWarRoom() {
        const name = document.getElementById('wr-name').value.trim();
        if (!name) { toast('Name is required', 'error'); return; }

        const payload = {
            name,
            priority: document.getElementById('wr-priority').value,
            affected_module: document.getElementById('wr-module').value.trim() || null,
            war_room_lead: document.getElementById('wr-lead').value.trim(),
            description: document.getElementById('wr-desc').value.trim(),
        };

        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/war-rooms`,
            { method: 'POST', body: JSON.stringify(payload) }
        );
        if (ok) {
            toast(`War Room ${data.code} created`, 'success');
            App.closeModal();
            refresh();
        } else {
            toast(data.error || 'Failed to create war room', 'error');
        }
    }

    async function openWarRoom(wrId) {
        const { ok, data: wr } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/war-rooms/${wrId}`
        );
        if (!ok) { toast('War room not found', 'error'); return; }

        const isClosed = wr.status === 'closed';

        // Fetch assigned incidents
        const allIncs = _incidents.filter(i => i.war_room_id === wrId);
        const incTable = allIncs.length > 0
            ? `<table class="data-table" style="font-size:0.9em;">
                <thead><tr><th>Code</th><th>Title</th><th>Severity</th><th>Status</th></tr></thead>
                <tbody>${allIncs.map(i => `
                    <tr>
                        <td><span class="code-badge">${i.code || '#'}</span></td>
                        <td>${i.title}</td>
                        <td><span class="badge ${severityColor[i.severity] || ''}">${i.severity}</span></td>
                        <td>${i.status}</td>
                    </tr>`).join('')}
                </tbody></table>`
            : '<p style="color:var(--sap-text-secondary);font-size:0.9em;">No incidents assigned.</p>';

        const assignedCRs = _changeRequests.filter(c => c.war_room_id === wrId);
        const crTable = assignedCRs.length > 0
            ? `<table class="data-table" style="font-size:0.9em;">
                <thead><tr><th>CR#</th><th>Title</th><th>Priority</th><th>Status</th></tr></thead>
                <tbody>${assignedCRs.map(c => `
                    <tr>
                        <td><span class="code-badge">${c.cr_number}</span></td>
                        <td>${c.title}</td>
                        <td><span class="badge ${severityColor[c.priority] || ''}">${c.priority}</span></td>
                        <td>${c.status}</td>
                    </tr>`).join('')}
                </tbody></table>`
            : '<p style="color:var(--sap-text-secondary);font-size:0.9em;">No change requests assigned.</p>';

        const html = `<div class="modal">
            <div class="modal__header">
                <h3>${wr.code} \u2014 ${wr.name}</h3>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal__body">
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;">
                    <span class="badge ${severityColor[wr.priority] || ''}">${wr.priority}</span>
                    <span class="badge badge--${wr.status === 'active' ? 'blue' : 'gray'}">${wr.status}</span>
                    ${wr.affected_module ? `<span style="font-size:0.9em;">${wr.affected_module}</span>` : ''}
                    ${wr.war_room_lead ? `<span style="font-size:0.9em;">Lead: ${wr.war_room_lead}</span>` : ''}
                </div>
                ${wr.description ? `<p style="font-size:0.9em;">${wr.description}</p>` : ''}

                <h4 style="margin:12px 0 6px;">Assigned Incidents (${allIncs.length})</h4>
                ${incTable}

                <h4 style="margin:12px 0 6px;">Assigned Change Requests (${assignedCRs.length})</h4>
                ${crTable}

                ${!isClosed ? `
                <div style="margin-top:16px;display:flex;gap:8px;">
                    <button class="btn btn--danger btn--sm" onclick="HypercareView.closeWarRoom(${wr.id})">Close War Room</button>
                </div>` : ''}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function closeWarRoom(wrId) {
        if (!window.confirm('Close this war room?')) return;
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/war-rooms/${wrId}/close`,
            { method: 'POST' }
        );
        if (ok) { toast('War room closed', 'success'); App.closeModal(); refresh(); }
        else toast(data.error || 'Failed', 'error');
    }

    // -- Exit Criteria Actions -----------------------------------------------

    async function seedExitCriteria() {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/exit-criteria/seed`,
            { method: 'POST' }
        );
        if (ok) {
            const count = (data.items || []).length;
            toast(count > 0 ? `${count} exit criteria seeded` : 'Criteria already exist', 'success');
            refresh();
        } else {
            toast(data.error || 'Failed', 'error');
        }
    }

    async function evaluateExitCriteria() {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/exit-criteria/evaluate`
        );
        if (ok) {
            toast(data.ready ? 'READY for exit' : data.recommendation || 'Evaluated', 'info');
            _loadExitCriteria().then(() => {
                if (_container) {
                    _container.innerHTML = _renderHTML();
                    _renderTabContent(_currentTab);
                }
            });
        } else {
            toast(data.error || 'Evaluation failed', 'error');
        }
    }

    async function requestExitSignoff() {
        if (!window.confirm('Request formal hypercare exit sign-off?')) return;
        const programId = App.getActiveProgram ? App.getActiveProgram().id : null;
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/exit-criteria/signoff`,
            { method: 'POST', body: JSON.stringify({ program_id: programId, approver_id: 1 }) }
        );
        if (ok) {
            toast('Exit sign-off approved', 'success');
            refresh();
        } else {
            toast(data.error || 'Sign-off failed', 'error');
        }
    }

    // -- Lesson Pipeline -----------------------------------------------------

    async function createLessonFromIncident(incidentId) {
        const { ok, data } = await API(
            `/api/v1/run-sustain/plans/${_planId}/hypercare/incidents/${incidentId}/create-lesson`,
            { method: 'POST' }
        );
        if (ok) {
            toast('Lesson created from incident', 'success');
            App.closeModal();
        } else {
            toast(data.error || 'Failed to create lesson', 'error');
        }
    }

    // -- Cleanup / Destroy ---------------------------------------------------

    function destroy() {
        _stopPolling();
        _planId = null;
        _container = null;
    }

    // -- Expose --------------------------------------------------------------
    return {
        render,
        refresh,
        destroy,
        switchTab,
        filterStatus,
        filterSeverity,
        showCreateIncident,
        _submitCreateIncident,
        openIncident,
        _firstResponse,
        quickResolve,
        _assignIncidentWarRoom,
        showEscalateModal,
        _submitEscalation,
        acknowledgeEscalation,
        seedEscalationRules,
        showCreateCR,
        _submitCreateCR,
        approveCR,
        rejectCR,
        showCreateWarRoom,
        _submitCreateWarRoom,
        openWarRoom,
        closeWarRoom,
        seedExitCriteria,
        evaluateExitCriteria,
        requestExitSignoff,
        createLessonFromIncident,
    };
})();
