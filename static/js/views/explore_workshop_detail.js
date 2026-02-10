/**
 * Explore Phase — Module C: Workshop Detail
 * F-018: WorkshopDetailPage    F-019: WorkshopHeader    F-020: SummaryStrip
 * F-021: ProcessStepList       F-022: ProcessStepCard   F-023: FitDecisionSelector
 * F-024: DecisionCard          F-025: OpenItemCard      F-026: RequirementCard
 * F-027: InlineAddForm         F-028: AgendaTimeline    F-029: AttendeeList
 * F-030: L3ConsolidatedDecision
 *
 * Route: /explore/workshops/:id (via App.navigate)
 */
const ExploreWorkshopDetailView = (() => {
    'use strict';

    const esc = ExpUI.esc;

    // ── State ────────────────────────────────────────────────────────
    let _pid = null;
    let _wsId = null;
    let _workshop = null;
    let _steps = [];
    let _decisions = [];
    let _openItems = [];
    let _requirements = [];
    let _fitDecisions = [];
    let _agendaItems = [];
    let _attendees = [];
    let _sessions = [];

    let _activeTab = 'steps';        // steps | decisions | openItems | requirements | agenda | attendees
    let _expandedStepId = null;
    let _showInlineForm = null;       // null | {type: 'decision'|'openItem'|'requirement', stepId}

    // ── API ──────────────────────────────────────────────────────────
    async function fetchAll() {
        const p = _pid, w = _wsId;
        const [ws, steps, decisions, openItems, requirements, fitDec, agenda, attendees, sessions] = await Promise.allSettled([
            ExploreAPI.workshops.get(p, w),
            ExploreAPI.levels.listL4(p),
            ExploreAPI.decisions.list(p, w),
            ExploreAPI.openItems.list(p),
            ExploreAPI.requirements.list(p),
            ExploreAPI.fitDecisions.list(p, w),
            ExploreAPI.agenda.list(p, w),
            ExploreAPI.attendees.list(p, w),
            ExploreAPI.sessions.list(p, w),
        ]);
        _workshop     = ws.status === 'fulfilled' ? ws.value : null;
        _steps        = steps.status === 'fulfilled' ? (steps.value || []) : [];
        _decisions    = decisions.status === 'fulfilled' ? (decisions.value || []) : [];
        _openItems    = openItems.status === 'fulfilled' ? (openItems.value || []) : [];
        _requirements = requirements.status === 'fulfilled' ? (requirements.value || []) : [];
        _fitDecisions = fitDec.status === 'fulfilled' ? (fitDec.value || []) : [];
        _agendaItems  = agenda.status === 'fulfilled' ? (agenda.value || []) : [];
        _attendees    = attendees.status === 'fulfilled' ? (attendees.value || []) : [];
        _sessions     = sessions.status === 'fulfilled' ? (sessions.value || []) : [];

        // Filter steps/reqs/OIs related to this workshop
        if (_workshop) {
            _steps = _steps.filter(s => s.workshop_id === _wsId || s.l3_scope_item_id === _workshop.l3_scope_item_id);
            _openItems = _openItems.filter(o => o.workshop_id === _wsId);
            _requirements = _requirements.filter(r => r.workshop_id === _wsId);
        }
    }

    // ── Workshop Header (F-019) ──────────────────────────────────────
    function renderHeader() {
        const w = _workshop;
        if (!w) return '';
        const canStart = w.status === 'scheduled' || w.status === 'draft';
        const canComplete = w.status === 'in_progress';
        const canReopen = w.status === 'completed';

        return `<div class="exp-card" style="margin-bottom:var(--exp-space-md)">
            <div class="exp-card__body" style="display:flex;flex-wrap:wrap;gap:var(--exp-space-lg);align-items:flex-start">
                <div style="flex:1;min-width:200px">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                        <code style="font-family:var(--exp-font-mono);font-size:13px;color:var(--sap-text-secondary)">${esc(w.code || '')}</code>
                        ${ExpUI.workshopStatusPill(w.status)}
                        ${w.workshop_type ? ExpUI.pill({ label: w.workshop_type, variant: 'info' }) : ''}
                    </div>
                    <h2 style="font-size:var(--exp-font-size-xl);margin:0 0 8px 0">${esc(w.name || '')}</h2>
                    <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:13px;color:var(--sap-text-secondary)">
                        ${w.scheduled_date ? `<span>📅 ${esc(w.scheduled_date)}</span>` : ''}
                        ${w.scheduled_time ? `<span>🕐 ${esc(w.scheduled_time)}</span>` : ''}
                        ${w.facilitator ? `<span>👤 ${esc(w.facilitator)}</span>` : ''}
                        ${w.area_code ? `<span>${ExpUI.areaPill(w.area_code)}</span>` : ''}
                        ${w.wave ? `<span>${ExpUI.wavePill(w.wave)}</span>` : ''}
                    </div>
                    ${w.scope_item_name||w.scope_item_code ? `<div style="margin-top:8px;font-size:13px">📋 Scope: <strong>${esc(w.scope_item_name||w.scope_item_code||'')}</strong></div>` : ''}
                    ${w.description ? `<div style="margin-top:8px;font-size:13px;color:var(--sap-text-secondary)">${esc(w.description)}</div>` : ''}
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;align-self:flex-start">
                    ${canStart ? ExpUI.actionButton({ label: 'Start Workshop', variant: 'success', size: 'sm', icon: '▶️', onclick: `ExploreWorkshopDetailView.transitionWorkshop('start')` }) : ''}
                    ${canComplete ? ExpUI.actionButton({ label: 'Complete', variant: 'primary', size: 'sm', icon: '✓', onclick: `ExploreWorkshopDetailView.transitionWorkshop('complete')` }) : ''}
                    ${canReopen ? ExpUI.actionButton({ label: 'Reopen', variant: 'warning', size: 'sm', icon: '↩', onclick: `ExploreWorkshopDetailView.transitionWorkshop('reopen')` }) : ''}
                    ${canComplete ? ExpUI.actionButton({ label: 'Create Delta', variant: 'secondary', size: 'sm', icon: '➕', onclick: `ExploreWorkshopDetailView.createDeltaWorkshop()` }) : ''}
                    ${ExpUI.actionButton({ label: '←', variant: 'ghost', size: 'sm', onclick: `App.navigate('explore-workshops')`, title: 'Back to Hub' })}
                </div>
            </div>
            ${renderDependenciesSection()}
        </div>`;
    }

    function renderDependenciesSection() {
        if (!_workshop || !_workshop.dependencies || !_workshop.dependencies.length) return '';
        return `<div style="border-top:1px solid #e2e8f0;padding:8px var(--exp-space-lg);font-size:12px;color:var(--sap-text-secondary)">
            <strong>Dependencies:</strong> ${_workshop.dependencies.map(d =>
                `<span style="margin-left:6px">${esc(d.depends_on_code || d.depends_on_id || '')} ${d.dependency_type === 'must_complete_first' ? '(must complete first)' : ''}</span>`
            ).join(', ')}
        </div>`;
    }

    // ── Summary Strip (F-020) ────────────────────────────────────────
    function renderSummaryStrip() {
        const fitC = _fitDecisions.filter(f => f.fit_status === 'fit').length;
        const partC = _fitDecisions.filter(f => f.fit_status === 'partial_fit').length;
        const gapC = _fitDecisions.filter(f => f.fit_status === 'gap').length;

        return `<div class="exp-kpi-strip" style="margin-bottom:var(--exp-space-md)">
            ${ExpUI.kpiBlock({ value: fitC, label: 'Fit', accent: 'var(--exp-fit)' })}
            ${ExpUI.kpiBlock({ value: partC, label: 'Partial', accent: 'var(--exp-partial)' })}
            ${ExpUI.kpiBlock({ value: gapC, label: 'Gap', accent: 'var(--exp-gap)' })}
            ${ExpUI.kpiBlock({ value: _decisions.length, label: 'Decisions', accent: 'var(--exp-decision)' })}
            ${ExpUI.kpiBlock({ value: _openItems.length, label: 'Open Items', accent: 'var(--exp-open-item)' })}
            ${ExpUI.kpiBlock({ value: _requirements.length, label: 'Requirements', accent: 'var(--exp-requirement)' })}
        </div>`;
    }

    // ── Tabs ─────────────────────────────────────────────────────────
    function renderTabs() {
        const tabs = [
            { key: 'steps',        label: 'Process Steps',  count: _steps.length },
            { key: 'decisions',    label: 'Decisions',      count: _decisions.length },
            { key: 'openItems',    label: 'Open Items',     count: _openItems.length },
            { key: 'requirements', label: 'Requirements',   count: _requirements.length },
            { key: 'agenda',       label: 'Agenda',         count: _agendaItems.length },
            { key: 'attendees',    label: 'Attendees',      count: _attendees.length },
        ];
        return `<div class="exp-tabs" style="margin-bottom:var(--exp-space-lg)">
            ${tabs.map(t => `<button class="exp-tab${_activeTab === t.key ? ' exp-tab--active' : ''}"
                onclick="ExploreWorkshopDetailView.setTab('${t.key}')">${t.label} ${ExpUI.countChip(t.count)}</button>`).join('')}
        </div>`;
    }

    // ── Process Steps Tab (F-021 + F-022) ────────────────────────────
    function renderStepsTab() {
        if (!_steps.length) {
            return `<div class="exp-empty"><div class="exp-empty__icon">⚙️</div><div class="exp-empty__title">No process steps</div></div>`;
        }
        return `<div style="display:flex;flex-direction:column;gap:var(--exp-space-sm)">
            ${_steps.map(step => renderProcessStepCard(step)).join('')}
        </div>`;
    }

    // ── Process Step Card (F-022) ────────────────────────────────────
    function renderProcessStepCard(step) {
        const isExpanded = _expandedStepId === step.id;
        const fd = _fitDecisions.find(f => f.l4_process_step_id === step.id);
        const fitStatus = fd ? fd.fit_status : (step.fit_status || 'pending');
        const stepDecs = _decisions.filter(d => d.l4_process_step_id === step.id);
        const stepOIs = _openItems.filter(o => o.l4_process_step_id === step.id);
        const stepReqs = _requirements.filter(r => r.l4_process_step_id === step.id);
        const prevSession = step.previous_session_id ? '🔄' : '';

        return `<div class="exp-card" style="border-left:3px solid ${fitStatusBorderColor(fitStatus)}">
            <div style="display:flex;align-items:center;gap:8px;padding:10px var(--exp-space-lg);cursor:pointer"
                 onclick="ExploreWorkshopDetailView.toggleStep('${step.id}')">
                <span class="exp-expandable-row__chevron${isExpanded ? ' exp-expandable-row__chevron--open' : ''}">▶</span>
                ${ExpUI.levelBadge('L4')}
                <code style="font-family:var(--exp-font-mono);font-size:11px;color:var(--sap-text-secondary)">${esc(step.code || step.sap_code || '')}</code>
                <span style="font-weight:500;flex:1" class="exp-truncate">${esc(step.name || '')}</span>
                ${prevSession ? `<span title="Continued from previous session">${prevSession}</span>` : ''}
                ${ExpUI.fitBadge(fitStatus)}
                ${ExpUI.countChip(stepDecs.length, { variant: 'decision', label: 'DEC' })}
                ${ExpUI.countChip(stepOIs.length, { variant: 'open_item', label: 'OI' })}
                ${ExpUI.countChip(stepReqs.length, { variant: 'requirement', label: 'REQ' })}
            </div>
            ${isExpanded ? renderStepExpanded(step, fitStatus, stepDecs, stepOIs, stepReqs) : ''}
        </div>`;
    }

    function fitStatusBorderColor(status) {
        const m = { fit: 'var(--exp-fit)', gap: 'var(--exp-gap)', partial_fit: 'var(--exp-partial)', pending: 'var(--exp-pending)' };
        return m[status] || 'var(--exp-pending)';
    }

    function renderStepExpanded(step, fitStatus, stepDecs, stepOIs, stepReqs) {
        return `<div class="exp-expandable-detail">
            ${step.notes ? `<div style="margin-bottom:12px;font-size:13px;color:var(--sap-text-secondary)">${esc(step.notes)}</div>` : ''}

            ${renderFitDecisionSelector(step, fitStatus)}

            <div style="margin-top:12px">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                    <strong style="font-size:13px;color:var(--exp-decision)">Decisions (${stepDecs.length})</strong>
                    ${ExpUI.actionButton({ label: '+ Decision', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.showInlineForm('decision','${step.id}')` })}
                </div>
                ${stepDecs.map(d => renderDecisionCard(d)).join('') || '<p style="font-size:12px;color:var(--sap-text-secondary)">No decisions yet</p>'}
            </div>

            <div style="margin-top:12px">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                    <strong style="font-size:13px;color:var(--exp-open-item)">Open Items (${stepOIs.length})</strong>
                    ${ExpUI.actionButton({ label: '+ Open Item', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.showInlineForm('openItem','${step.id}')` })}
                </div>
                ${stepOIs.map(o => renderOpenItemCard(o)).join('') || '<p style="font-size:12px;color:var(--sap-text-secondary)">No open items</p>'}
            </div>

            <div style="margin-top:12px">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                    <strong style="font-size:13px;color:var(--exp-requirement)">Requirements (${stepReqs.length})</strong>
                    ${ExpUI.actionButton({ label: '+ Requirement', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.showInlineForm('requirement','${step.id}')` })}
                </div>
                ${stepReqs.map(r => renderRequirementCard(r)).join('') || '<p style="font-size:12px;color:var(--sap-text-secondary)">No requirements</p>'}
            </div>

            ${_showInlineForm && _showInlineForm.stepId === step.id ? renderInlineAddForm(_showInlineForm.type, step.id) : ''}

            <div style="margin-top:12px;text-align:right">
                ${ExpUI.actionButton({ label: '🚩 Flag', variant: 'ghost', size: 'sm', title: 'Flag for cross-module attention', onclick: `ExploreWorkshopDetailView.flagStep('${step.id}')` })}
            </div>
        </div>`;
    }

    // ── Fit Decision Selector (F-023) ────────────────────────────────
    function renderFitDecisionSelector(step, currentFit) {
        const fits = ['fit','partial_fit','gap'];
        return `<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f1f5f9">
            <span style="font-size:12px;font-weight:600;color:var(--sap-text-secondary)">Fit Decision:</span>
            ${fits.map(f => {
                const isActive = currentFit === f;
                const colors = { fit: 'var(--exp-fit)', partial_fit: 'var(--exp-partial)', gap: 'var(--exp-gap)' };
                const labels = { fit: 'Fit', partial_fit: 'Partial Fit', gap: 'Gap' };
                return `<label style="display:inline-flex;align-items:center;gap:4px;cursor:pointer;padding:4px 10px;border-radius:var(--exp-radius-pill);background:${isActive ? colors[f] + '20' : '#f1f5f9'};border:2px solid ${isActive ? colors[f] : 'transparent'};font-size:12px;font-weight:600;color:${isActive ? colors[f] : 'var(--sap-text-secondary)'}">
                    <input type="radio" name="fitDecision_${step.id}" value="${f}" ${isActive ? 'checked' : ''} style="display:none"
                           onchange="ExploreWorkshopDetailView.setFitDecision('${step.id}','${f}')">
                    ${labels[f]}
                </label>`;
            }).join('')}
        </div>`;
    }

    // ── Decision Card (F-024) ────────────────────────────────────────
    function renderDecisionCard(d) {
        return `<div class="exp-card" style="border-left:3px solid var(--exp-decision);padding:10px 14px;margin-bottom:6px">
            <div style="display:flex;align-items:flex-start;gap:8px">
                <div style="flex:1">
                    <div style="font-weight:600;font-size:13px">${esc(d.text || d.description || d.title || '')}</div>
                    <div style="font-size:11px;color:var(--sap-text-secondary);margin-top:4px">
                        ${d.decided_by ? `👤 ${esc(d.decided_by)}` : ''}
                        ${d.category ? ` · ${ExpUI.pill({ label: d.category, variant: 'decision', size: 'sm' })}` : ''}
                    </div>
                </div>
                <code style="font-size:10px;color:var(--sap-text-secondary)">${esc(d.code || '')}</code>
            </div>
        </div>`;
    }

    // ── Open Item Card (F-025) ───────────────────────────────────────
    function renderOpenItemCard(o) {
        const overdue = o.due_date && new Date(o.due_date) < new Date() && o.status !== 'closed' && o.status !== 'resolved';
        return `<div class="exp-card" style="border-left:3px solid var(--exp-open-item);padding:10px 14px;margin-bottom:6px">
            <div style="display:flex;align-items:flex-start;gap:8px">
                <div style="flex:1">
                    <div style="display:flex;align-items:center;gap:6px">
                        <code style="font-size:11px;color:var(--sap-text-secondary)">${esc(o.code || '')}</code>
                        ${ExpUI.priorityPill(o.priority)}
                        ${ExpUI.oiStatusPill(o.status)}
                    </div>
                    <div style="font-weight:500;font-size:13px;margin-top:4px">${esc(o.title || '')}</div>
                    <div style="font-size:11px;color:var(--sap-text-secondary);margin-top:4px">
                        ${o.assignee ? `👤 ${esc(o.assignee)}` : ''}
                        ${o.due_date ? ` · 📅 <span style="color:${overdue ? 'var(--exp-gap)' : 'inherit'};font-weight:${overdue ? '700' : 'normal'}">${esc(o.due_date)}${overdue ? ' ⚠ OVERDUE' : ''}</span>` : ''}
                    </div>
                </div>
            </div>
        </div>`;
    }

    // ── Requirement Card (F-026) ─────────────────────────────────────
    function renderRequirementCard(r) {
        return `<div class="exp-card" style="border-left:3px solid var(--exp-requirement);padding:10px 14px;margin-bottom:6px">
            <div style="display:flex;align-items:flex-start;gap:8px">
                <div style="flex:1">
                    <div style="display:flex;align-items:center;gap:6px">
                        <code style="font-size:11px;color:var(--sap-text-secondary)">${esc(r.code || '')}</code>
                        ${ExpUI.priorityPill(r.priority)}
                        ${r.requirement_type ? ExpUI.pill({ label: r.requirement_type, variant: 'info', size: 'sm' }) : ''}
                    </div>
                    <div style="font-weight:500;font-size:13px;margin-top:4px">${esc(r.title || '')}</div>
                    <div style="margin-top:6px">${ExpUI.statusFlowIndicator(r.status || 'draft')}</div>
                    ${r.estimated_effort ? `<div style="font-size:11px;color:var(--sap-text-secondary);margin-top:4px">Effort: ${esc(String(r.estimated_effort))} days</div>` : ''}
                </div>
            </div>
        </div>`;
    }

    // ── Inline Add Form (F-027) ──────────────────────────────────────
    function renderInlineAddForm(type, stepId) {
        const forms = {
            decision: `<div class="exp-inline-form" style="margin-top:12px">
                <h4 style="margin-bottom:8px;color:var(--exp-decision)">New Decision</h4>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Decision Text</label><textarea id="inlineDecText" rows="2" placeholder="What was decided?"></textarea></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Decided By</label><input id="inlineDecBy" type="text" placeholder="Name"></div>
                    <div class="exp-inline-form__field"><label>Category</label>
                        <select id="inlineDecCat"><option value="configuration">Configuration</option><option value="customization">Customization</option><option value="process_change">Process Change</option><option value="integration">Integration</option><option value="other">Other</option></select>
                    </div>
                </div>
                <div class="exp-inline-form__actions">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', size: 'sm', onclick: 'ExploreWorkshopDetailView.hideInlineForm()' })}
                    ${ExpUI.actionButton({ label: 'Save', variant: 'primary', size: 'sm', onclick: `ExploreWorkshopDetailView.submitInlineForm('decision','${stepId}')` })}
                </div>
            </div>`,

            openItem: `<div class="exp-inline-form" style="margin-top:12px">
                <h4 style="margin-bottom:8px;color:var(--exp-open-item)">New Open Item</h4>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Title</label><input id="inlineOITitle" type="text" placeholder="Open item title"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Priority</label>
                        <select id="inlineOIPriority"><option value="P1">P1 - Critical</option><option value="P2">P2 - High</option><option value="P3" selected>P3 - Medium</option><option value="P4">P4 - Low</option></select>
                    </div>
                    <div class="exp-inline-form__field"><label>Assignee</label><input id="inlineOIAssignee" type="text" placeholder="Assignee name"></div>
                    <div class="exp-inline-form__field"><label>Due Date</label><input id="inlineOIDue" type="date"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Description</label><textarea id="inlineOIDesc" rows="2" placeholder="Details"></textarea></div>
                </div>
                <div class="exp-inline-form__actions">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', size: 'sm', onclick: 'ExploreWorkshopDetailView.hideInlineForm()' })}
                    ${ExpUI.actionButton({ label: 'Save', variant: 'primary', size: 'sm', onclick: `ExploreWorkshopDetailView.submitInlineForm('openItem','${stepId}')` })}
                </div>
            </div>`,

            requirement: `<div class="exp-inline-form" style="margin-top:12px">
                <h4 style="margin-bottom:8px;color:var(--exp-requirement)">New Requirement</h4>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Title</label><input id="inlineReqTitle" type="text" placeholder="Requirement title"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Priority</label>
                        <select id="inlineReqPriority"><option value="P1">P1</option><option value="P2">P2</option><option value="P3" selected>P3</option><option value="P4">P4</option></select>
                    </div>
                    <div class="exp-inline-form__field"><label>Type</label>
                        <select id="inlineReqType"><option value="functional">Functional</option><option value="enhancement">Enhancement</option><option value="custom_development">Custom Dev</option><option value="integration">Integration</option><option value="report">Report</option></select>
                    </div>
                    <div class="exp-inline-form__field"><label>Effort (days)</label><input id="inlineReqEffort" type="number" min="0" step="0.5" placeholder="0"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Description</label><textarea id="inlineReqDesc" rows="2" placeholder="Requirement details"></textarea></div>
                </div>
                <div class="exp-inline-form__actions">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', size: 'sm', onclick: 'ExploreWorkshopDetailView.hideInlineForm()' })}
                    ${ExpUI.actionButton({ label: 'Save', variant: 'primary', size: 'sm', onclick: `ExploreWorkshopDetailView.submitInlineForm('requirement','${stepId}')` })}
                </div>
            </div>`,
        };
        return forms[type] || '';
    }

    // ── Decisions Tab ────────────────────────────────────────────────
    function renderDecisionsTab() {
        if (!_decisions.length) return emptyTab('decisions', '💬');
        return `<div style="display:flex;flex-direction:column;gap:6px">${_decisions.map(d => renderDecisionCard(d)).join('')}</div>`;
    }

    // ── Open Items Tab ───────────────────────────────────────────────
    function renderOpenItemsTab() {
        if (!_openItems.length) return emptyTab('open items', '⚠️');
        return `<div style="display:flex;flex-direction:column;gap:6px">${_openItems.map(o => renderOpenItemCard(o)).join('')}</div>`;
    }

    // ── Requirements Tab ─────────────────────────────────────────────
    function renderRequirementsTab() {
        if (!_requirements.length) return emptyTab('requirements', '📝');
        return `<div style="display:flex;flex-direction:column;gap:6px">${_requirements.map(r => renderRequirementCard(r)).join('')}</div>`;
    }

    // ── Agenda Timeline (F-028) ──────────────────────────────────────
    function renderAgendaTab() {
        if (!_agendaItems.length) return emptyTab('agenda items', '📋');
        const sorted = [..._agendaItems].sort((a, b) => (a.start_time || '').localeCompare(b.start_time || '') || (a.order_index || 0) - (b.order_index || 0));
        return `<div class="exp-timeline">
            ${sorted.map(a => `<div class="exp-timeline__item">
                <div class="exp-timeline__time">${esc(a.start_time || '')} — ${esc(a.end_time || '')}</div>
                <div class="exp-timeline__content">
                    <strong>${esc(a.title || '')}</strong>
                    ${a.description ? `<div style="font-size:12px;color:var(--sap-text-secondary)">${esc(a.description)}</div>` : ''}
                    ${a.presenter ? `<div style="font-size:11px;color:var(--sap-text-secondary)">👤 ${esc(a.presenter)}</div>` : ''}
                </div>
            </div>`).join('')}
        </div>`;
    }

    // ── Attendee List (F-029) ────────────────────────────────────────
    function renderAttendeesTab() {
        if (!_attendees.length) return emptyTab('attendees', '👥');
        return `<div style="display:flex;flex-direction:column">
            ${_attendees.map(a => `<div class="exp-attendee">
                <div class="exp-attendee__avatar">${esc((a.name||'?').charAt(0).toUpperCase())}</div>
                <div class="exp-attendee__info">
                    <div class="exp-attendee__name">${esc(a.name || '')}</div>
                    <div class="exp-attendee__role">${esc(a.role || '')} ${a.organization ? `· ${esc(a.organization)}` : ''}</div>
                </div>
                <div class="exp-attendee__status">
                    ${a.attendance_status === 'present' ? ExpUI.pill({ label: '✓ Present', variant: 'success', size: 'sm' })
                     : a.attendance_status === 'absent' ? ExpUI.pill({ label: '✗ Absent', variant: 'danger', size: 'sm' })
                     : ExpUI.pill({ label: 'Invited', variant: 'draft', size: 'sm' })}
                </div>
            </div>`).join('')}
        </div>`;
    }

    // ── L3 Consolidated Decision (F-030) ─────────────────────────────
    function renderL3ConsolidatedDecision() {
        if (!_workshop || _workshop.status !== 'completed') return '';
        const fitCounts = {
            fit: _fitDecisions.filter(f => f.fit_status === 'fit').length,
            gap: _fitDecisions.filter(f => f.fit_status === 'gap').length,
            partial_fit: _fitDecisions.filter(f => f.fit_status === 'partial_fit').length,
            pending: _fitDecisions.filter(f => !f.fit_status || f.fit_status === 'pending').length,
        };
        const total = Object.values(fitCounts).reduce((s, v) => s + v, 0);
        const suggested = total ? (fitCounts.gap > 0 ? 'gap' : fitCounts.partial_fit > 0 ? 'partial_fit' : 'fit') : 'pending';

        return `<div class="exp-card" style="margin-top:var(--exp-space-md);border:2px solid var(--exp-l3);border-radius:var(--exp-radius-lg)">
            <div class="exp-card__header" style="border-bottom:1px solid #e2e8f0">
                <h3 class="exp-card__title" style="color:var(--exp-l3)">L3 Consolidated Decision</h3>
            </div>
            <div class="exp-card__body">
                <div style="margin-bottom:12px">
                    <div style="font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px">L4 Breakdown</div>
                    ${ExpUI.fitBarMini(fitCounts, { height: 10 })}
                    <div style="display:flex;gap:12px;margin-top:6px;font-size:12px">
                        <span style="color:var(--exp-fit)">● Fit ${fitCounts.fit}</span>
                        <span style="color:var(--exp-partial)">◐ Partial ${fitCounts.partial_fit}</span>
                        <span style="color:var(--exp-gap)">● Gap ${fitCounts.gap}</span>
                        <span style="color:var(--exp-pending)">○ Pending ${fitCounts.pending}</span>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
                    <span style="font-size:13px;font-weight:600">System Suggestion:</span>
                    ${ExpUI.fitBadge(suggested)}
                </div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Accept Suggestion', variant: 'success', size: 'sm', onclick: `ExploreWorkshopDetailView.acceptL3Suggestion('${suggested}')` })}
                    ${ExpUI.actionButton({ label: 'Override', variant: 'warning', size: 'sm', onclick: 'ExploreWorkshopDetailView.overrideL3Decision()' })}
                </div>
            </div>
        </div>`;
    }

    function emptyTab(name, icon) {
        return `<div class="exp-empty"><div class="exp-empty__icon">${icon}</div><div class="exp-empty__title">No ${name} yet</div><p class="exp-empty__text">Items will appear here as they are added during the workshop</p></div>`;
    }

    // ── Actions ──────────────────────────────────────────────────────
    function setTab(t) { _activeTab = t; renderPage(); }

    function toggleStep(id) {
        _expandedStepId = _expandedStepId === id ? null : id;
        renderPage();
    }

    function showInlineForm(type, stepId) {
        _showInlineForm = { type, stepId };
        renderPage();
    }

    function hideInlineForm() {
        _showInlineForm = null;
        renderPage();
    }

    async function submitInlineForm(type, stepId) {
        try {
            if (type === 'decision') {
                await ExploreAPI.decisions.create(_pid, _wsId, {
                    l4_process_step_id: stepId,
                    text: document.getElementById('inlineDecText')?.value,
                    decided_by: document.getElementById('inlineDecBy')?.value,
                    category: document.getElementById('inlineDecCat')?.value,
                });
            } else if (type === 'openItem') {
                await ExploreAPI.openItems.create(_pid, {
                    workshop_id: _wsId,
                    l4_process_step_id: stepId,
                    title: document.getElementById('inlineOITitle')?.value,
                    priority: document.getElementById('inlineOIPriority')?.value,
                    assignee: document.getElementById('inlineOIAssignee')?.value,
                    due_date: document.getElementById('inlineOIDue')?.value || null,
                    description: document.getElementById('inlineOIDesc')?.value,
                });
            } else if (type === 'requirement') {
                await ExploreAPI.requirements.create(_pid, {
                    workshop_id: _wsId,
                    l4_process_step_id: stepId,
                    title: document.getElementById('inlineReqTitle')?.value,
                    priority: document.getElementById('inlineReqPriority')?.value,
                    requirement_type: document.getElementById('inlineReqType')?.value,
                    estimated_effort: parseFloat(document.getElementById('inlineReqEffort')?.value) || null,
                    description: document.getElementById('inlineReqDesc')?.value,
                });
            }
            _showInlineForm = null;
            App.toast(`${type === 'openItem' ? 'Open item' : type.charAt(0).toUpperCase() + type.slice(1)} created`, 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Creation failed', 'error');
        }
    }

    async function setFitDecision(stepId, status) {
        try {
            const existing = _fitDecisions.find(f => f.l4_process_step_id === stepId);
            if (existing) {
                await ExploreAPI.fitDecisions.update(_pid, _wsId, existing.id, { fit_status: status });
            } else {
                await ExploreAPI.fitDecisions.create(_pid, _wsId, { l4_process_step_id: stepId, fit_status: status });
            }
            App.toast('Fit decision updated', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed to update fit decision', 'error');
        }
    }

    async function transitionWorkshop(action) {
        try {
            await ExploreAPI.workshops.transition(_pid, _wsId, { action });
            App.toast(`Workshop ${action}ed`, 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || `Failed to ${action} workshop`, 'error');
        }
    }

    async function createDeltaWorkshop() {
        try {
            await ExploreAPI.workshops.create(_pid, {
                name: `${_workshop.name} (Delta)`,
                workshop_type: 'delta',
                l3_scope_item_id: _workshop.l3_scope_item_id,
                area_code: _workshop.area_code,
                wave: _workshop.wave,
                facilitator: _workshop.facilitator,
                parent_workshop_id: _wsId,
            });
            App.toast('Delta workshop created', 'success');
        } catch (err) {
            App.toast(err.message || 'Failed to create delta', 'error');
        }
    }

    function flagStep(stepId) {
        App.toast('Step flagged for cross-module attention', 'info');
    }

    async function acceptL3Suggestion(status) {
        if (!_workshop || !_workshop.l3_scope_item_id) {
            App.toast('No L3 scope item linked', 'warning');
            return;
        }
        try {
            await ExploreAPI.signoff.performL3(_pid, _workshop.l3_scope_item_id, { suggested_status: status });
            App.toast('L3 suggestion accepted', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed', 'error');
        }
    }

    function overrideL3Decision() {
        if (_workshop && _workshop.l3_scope_item_id) {
            ExploreHierarchyView.openSignOffDialog(_workshop.l3_scope_item_id, true);
        }
    }

    // ── Main Render (F-018) ──────────────────────────────────────────
    function renderPage() {
        const main = document.getElementById('mainContent');
        let tabContent = '';
        switch (_activeTab) {
            case 'steps':        tabContent = renderStepsTab(); break;
            case 'decisions':    tabContent = renderDecisionsTab(); break;
            case 'openItems':    tabContent = renderOpenItemsTab(); break;
            case 'requirements': tabContent = renderRequirementsTab(); break;
            case 'agenda':       tabContent = renderAgendaTab(); break;
            case 'attendees':    tabContent = renderAttendeesTab(); break;
        }

        main.innerHTML = `<div class="explore-page">
            ${renderHeader()}
            ${renderSummaryStrip()}
            ${renderTabs()}
            <div>${tabContent}</div>
            ${renderL3ConsolidatedDecision()}
        </div>`;
    }

    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        if (!prog) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">📋</div><div class="exp-empty__title">Select a program first</div></div>`;
            return;
        }
        _pid = prog.id;
        _wsId = localStorage.getItem('exp_selected_workshop');
        if (!_wsId) {
            App.navigate('explore-workshops');
            return;
        }

        main.innerHTML = `<div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:300px">
            <div style="text-align:center;color:var(--sap-text-secondary)"><div style="font-size:28px;margin-bottom:8px">⏳</div>Loading workshop…</div>
        </div>`;

        try {
            await fetchAll();
            if (!_workshop) {
                main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Workshop not found</div></div>`;
                return;
            }
            renderPage();
        } catch (err) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
        }
    }

    return {
        render, setTab, toggleStep,
        showInlineForm, hideInlineForm, submitInlineForm,
        setFitDecision, transitionWorkshop, createDeltaWorkshop,
        flagStep, acceptL3Suggestion, overrideL3Decision,
    };
})();
