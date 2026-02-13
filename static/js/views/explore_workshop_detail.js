/**
 * Explore Phase — Workshop Detail View
 * Faz 3 — Full rewrite fixing 7 critical bugs:
 *   BUG-1: fitDecisions.update → wrong endpoint → now uses POST /fit-decisions
 *   BUG-2: Decision/OI/Req creation lost process_step_id → now uses processSteps.addX
 *   BUG-3: openItems.list(pid) fetched ALL project OIs → now uses getFull() single call
 *   BUG-4: sessions data fetched but not rendered → now Sessions tab renders cards
 *   BUG-5: flagStep was no-op → now opens cross-module flag dialog
 *   BUG-6: createDeltaWorkshop used wrong field names → now uses workshops.createDelta
 *   BUG-7: Reopen had no reason prompt → now prompts for mandatory reason
 *
 * Single data source: ExploreAPI.workshops.full(pid, wsId) — all data in one call.
 */
const ExploreWorkshopDetailView = (() => {
    'use strict';

    const esc = ExpUI.esc;

    // ── State ────────────────────────────────────────────────────────
    let _pid = null;
    let _wsId = null;
    let _ws = null;         // full workshop payload from getFull()

    let _activeTab = 'steps';
    let _expandedStepId = null;
    let _showInlineForm = null; // { type: 'decision'|'openItem'|'requirement'|'flag', stepId }
    let _inlineBusy = false;
    let _lastScrollY = 0;

    // ── Computed helpers from _ws ────────────────────────────────────
    function workshop()     { return _ws?.workshop || {}; }
    function steps()        { return _ws?.process_steps || []; }
    function decisions()    { return _ws?.decisions || []; }
    function openItems()    { return _ws?.open_items || []; }
    function requirements() { return _ws?.requirements || []; }
    function fitDecisions() { return _ws?.fit_decisions || []; }
    function agendaItems()  { return _ws?.agenda_items || []; }
    function attendees()    { return _ws?.attendees || []; }
    function sessions()     { return _ws?.sessions || []; }

    // Documents are loaded separately because getFull doesn't include them
    let _documents = [];

    // ── Data Loading — SINGLE API call (BUG-3 fix) ──────────────────
    async function fetchAll() {
        const [full, docs] = await Promise.allSettled([
            ExploreAPI.workshops.full(_pid, _wsId),
            ExploreAPI.documents.list(_pid, _wsId),
        ]);
        _ws = full.status === 'fulfilled' ? full.value : null;
        _documents = docs.status === 'fulfilled' ? (Array.isArray(docs.value) ? docs.value : docs.value?.items || []) : [];
    }

    // ═══════════════════════════════════════════════════════════════════
    // HEADER
    // ═══════════════════════════════════════════════════════════════════
    function renderHeader() {
        const w = workshop();
        if (!w.id) return '';
        const canStart    = w.status === 'scheduled' || w.status === 'draft';
        const canComplete = w.status === 'in_progress';
        const canReopen   = w.status === 'completed';
        const dateStr = w.date || w.scheduled_date || '';
        const timeStr = w.start_time || w.scheduled_time || '';

        return `<div class="exp-card" style="margin-bottom:var(--exp-space-md)">
            <div class="exp-card__body" style="display:flex;flex-wrap:wrap;gap:var(--exp-space-lg);align-items:flex-start">
                <div style="flex:1;min-width:200px">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                        <code style="font-family:var(--exp-font-mono);font-size:13px;color:var(--sap-text-secondary)">${esc(w.code || '')}</code>
                        ${ExpUI.workshopStatusPill(w.status)}
                        ${w.type ? ExpUI.pill({ label: w.type.replace(/_/g, ' '), variant: 'info' }) : ''}
                        ${w.session_number ? `<span style="font-size:11px;color:var(--sap-text-secondary)">Session ${w.session_number}/${w.total_sessions || '?'}</span>` : ''}
                    </div>
                    <h2 style="font-size:var(--exp-font-size-xl);margin:0 0 8px 0">${esc(w.name || '')}</h2>
                    <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:13px;color:var(--sap-text-secondary)">
                        ${dateStr ? `<span>📅 ${esc(dateStr)}</span>` : ''}
                        ${timeStr ? `<span>🕐 ${esc(timeStr)}</span>` : ''}
                        ${w.facilitator_id ? `<span>👤 ${esc(w.facilitator_id)}</span>` : ''}
                        ${w.process_area ? `<span>${ExpUI.areaPill(w.process_area)}</span>` : ''}
                        ${w.wave ? `<span>${ExpUI.wavePill(w.wave)}</span>` : ''}
                    </div>
                    ${w.notes ? `<div style="margin-top:8px;font-size:13px;color:var(--sap-text-secondary)">${esc(w.notes)}</div>` : ''}
                    ${w.reopen_count ? `<div style="margin-top:4px;font-size:11px;color:var(--exp-gap)">↩ Reopened ${w.reopen_count} time(s)${w.reopen_reason ? ': ' + esc(w.reopen_reason) : ''}</div>` : ''}
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;align-self:flex-start">
                    ${canStart    ? ExpUI.actionButton({ label: '▶ Start',    variant: 'success',   size: 'sm', onclick: `ExploreWorkshopDetailView.startWorkshop()` }) : ''}
                    ${canComplete ? ExpUI.actionButton({ label: '✓ Complete', variant: 'primary',   size: 'sm', onclick: `ExploreWorkshopDetailView.completeWorkshop()` }) : ''}
                    ${canReopen   ? ExpUI.actionButton({ label: '↩ Reopen',   variant: 'warning',   size: 'sm', onclick: `ExploreWorkshopDetailView.reopenWorkshop()` }) : ''}
                    ${canReopen   ? ExpUI.actionButton({ label: '➕ Delta',    variant: 'secondary', size: 'sm', onclick: `ExploreWorkshopDetailView.createDeltaWorkshop()` }) : ''}
                    ${typeof DemoFlow !== 'undefined' && !DemoFlow.isActive() ? `<button class="btn btn-secondary btn-sm" onclick="DemoFlow.start('${w.id}')" title="Start guided demo flow">🎬 Demo Flow</button>` : ''}
                    ${ExpUI.actionButton({ label: '← Back', variant: 'ghost', size: 'sm', onclick: `App.navigate('explore-workshops')` })}
                </div>
            </div>
        </div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // KPI STRIP  (computed from steps, not fitDecisions endpoint)
    // ═══════════════════════════════════════════════════════════════════
    function renderKPIStrip() {
        const s = steps();
        const total     = s.length;
        const fitC      = s.filter(st => st.fit_decision === 'fit').length;
        const partialC  = s.filter(st => st.fit_decision === 'partial_fit').length;
        const gapC      = s.filter(st => st.fit_decision === 'gap').length;
        const assessed  = fitC + partialC + gapC;

        return `<div class="exp-kpi-strip" style="margin-bottom:var(--exp-space-md)">
            ${ExpUI.kpiBlock({ value: `${assessed}/${total}`, label: 'Assessed', accent: 'var(--sap-text-secondary)' })}
            ${ExpUI.kpiBlock({ value: fitC,     label: 'Fit',          accent: 'var(--exp-fit)' })}
            ${ExpUI.kpiBlock({ value: partialC, label: 'Partial',      accent: 'var(--exp-partial)' })}
            ${ExpUI.kpiBlock({ value: gapC,     label: 'Gap',          accent: 'var(--exp-gap)' })}
            ${ExpUI.kpiBlock({ value: decisions().length,    label: 'Decisions',    accent: 'var(--exp-decision)' })}
            ${ExpUI.kpiBlock({ value: openItems().length,    label: 'Open Items',   accent: 'var(--exp-open-item)' })}
            ${ExpUI.kpiBlock({ value: requirements().length, label: 'Requirements', accent: 'var(--exp-requirement)' })}
        </div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // TABS
    // ═══════════════════════════════════════════════════════════════════
    function renderTabs() {
        const tabs = [
            { key: 'steps',        label: 'Process Steps',  count: steps().length },
            { key: 'decisions',    label: 'Decisions',      count: decisions().length },
            { key: 'openItems',    label: 'Open Items',     count: openItems().length },
            { key: 'requirements', label: 'Requirements',   count: requirements().length },
            { key: 'agenda',       label: 'Agenda',         count: agendaItems().length },
            { key: 'attendees',    label: 'Attendees',      count: attendees().length },
            { key: 'sessions',     label: 'Sessions',       count: sessions().length },
            { key: 'documents',    label: 'Documents',      count: _documents.length },
        ];
        return `<div class="exp-tabs" style="margin-bottom:var(--exp-space-lg)">
            ${tabs.map(t => `<button class="exp-tab${_activeTab === t.key ? ' exp-tab--active' : ''}"
                onclick="ExploreWorkshopDetailView.setTab('${t.key}')">${t.label} ${ExpUI.countChip(t.count)}</button>`).join('')}
        </div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEPS TAB — Grouped by L3
    // ═══════════════════════════════════════════════════════════════════
    function renderStepsTab() {
        const s = steps();
        if (!s.length) return emptyTab('process steps', '⚙️');

        // Group steps by parent L3 (process_level_id → L4 → parent is L3)
        const grouped = {};
        for (const step of s) {
            const l3Key = step.parent_id || 'ungrouped';
            // Use L3 parent fields from backend (Bug C fix), fallback to process_area_code
            const l3Name = step.l3_parent_code
                ? `${step.l3_parent_process_area_code || ''} — ${step.l3_parent_name || ''}`.replace(/^\s*—\s*/, '')
                : step.process_area_code
                    ? `${step.process_area_code} — ${step.name || ''}`
                    : step.name || 'Process Step';
            if (!grouped[l3Key]) grouped[l3Key] = { name: l3Name, steps: [] };
            grouped[l3Key].steps.push(step);
        }

        // Always show L3 group headers (Bug A fix)
        const groups = Object.values(grouped);
        return groups.map(g => `
            <div style="margin-bottom:var(--exp-space-lg)">
                <div style="font-weight:600;font-size:14px;color:var(--exp-l3);margin-bottom:8px;padding-left:4px">
                    ${ExpUI.levelBadge('L3')} ${esc(g.name)}
                </div>
                <div style="display:flex;flex-direction:column;gap:var(--exp-space-sm)">
                    ${g.steps.map(step => renderProcessStepCard(step)).join('')}
                </div>
            </div>
        `).join('');
    }

    // ── Process Step Card ────────────────────────────────────────────
    function renderProcessStepCard(step) {
        const isExpanded = _expandedStepId === step.id;
        const fitStatus = step.fit_decision || 'pending';
        const stepDecs  = decisions().filter(d => d.process_step_id === step.id);
        const stepOIs   = openItems().filter(o => o.process_step_id === step.id);
        const stepReqs  = requirements().filter(r => r.process_step_id === step.id);
        const carried   = step.carried_from_session ? '🔄' : '';

        return `<div class="exp-card" style="border-left:3px solid ${fitColor(fitStatus)}">
            <div style="display:flex;align-items:center;gap:8px;padding:10px var(--exp-space-lg);cursor:pointer"
                 onclick="ExploreWorkshopDetailView.toggleStep('${step.id}')">
                <span class="exp-expandable-row__chevron${isExpanded ? ' exp-expandable-row__chevron--open' : ''}">▶</span>
                ${ExpUI.levelBadge('L4')}
                <code style="font-family:var(--exp-font-mono);font-size:11px;color:var(--sap-text-secondary)">${esc(step.code || step.sap_code || '')}</code>
                <span style="font-weight:500;flex:1" class="exp-truncate">${esc(step.name || '')}</span>
                ${carried ? `<span title="Carried from session ${step.carried_from_session}">${carried}</span>` : ''}
                ${ExpUI.fitBadge(fitStatus)}
                ${stepDecs.length  ? ExpUI.countChip(stepDecs.length,  { variant: 'decision',    label: 'DEC' }) : ''}
                ${stepOIs.length   ? ExpUI.countChip(stepOIs.length,   { variant: 'open_item',   label: 'OI' })  : ''}
                ${stepReqs.length  ? ExpUI.countChip(stepReqs.length,  { variant: 'requirement', label: 'REQ' }) : ''}
            </div>
            ${isExpanded ? renderStepExpanded(step, fitStatus, stepDecs, stepOIs, stepReqs) : ''}
        </div>`;
    }

    function fitColor(status) {
        const m = { fit: 'var(--exp-fit)', gap: 'var(--exp-gap)', partial_fit: 'var(--exp-partial)', pending: 'var(--exp-pending)' };
        return m[status] || 'var(--exp-pending)';
    }

    // ── Step Expanded Detail ─────────────────────────────────────────
    function renderStepExpanded(step, fitStatus, stepDecs, stepOIs, stepReqs) {
        const wsInProgress = workshop().status === 'in_progress';

        return `<div class="exp-expandable-detail">
            ${step.notes ? `<div style="margin-bottom:12px;font-size:13px;color:var(--sap-text-secondary)">${esc(step.notes)}</div>` : ''}

            ${wsInProgress ? renderFitDecisionSelector(step, fitStatus) : renderFitReadonly(fitStatus)}

            ${wsInProgress ? `<div style="display:flex;gap:8px;margin:12px 0;align-items:center">
                <label style="font-size:12px;display:flex;align-items:center;gap:4px;cursor:pointer">
                    <input type="checkbox" ${step.demo_shown ? 'checked' : ''} onchange="ExploreWorkshopDetailView.toggleStepFlag('${step.id}','demo_shown',this.checked)"> Demo shown
                </label>
                <label style="font-size:12px;display:flex;align-items:center;gap:4px;cursor:pointer">
                    <input type="checkbox" ${step.bpmn_reviewed ? 'checked' : ''} onchange="ExploreWorkshopDetailView.toggleStepFlag('${step.id}','bpmn_reviewed',this.checked)"> BPMN reviewed
                </label>
            </div>` : ''}

            ${renderChildSection('Decisions', 'exp-decision', stepDecs, renderDecisionCard, 'decision', step.id, wsInProgress)}
            ${renderChildSection('Open Items', 'exp-open-item', stepOIs, renderOpenItemCard, 'openItem', step.id, wsInProgress)}
            ${renderChildSection('Requirements', 'exp-requirement', stepReqs, renderRequirementCard, 'requirement', step.id, wsInProgress)}

            ${_showInlineForm && _showInlineForm.stepId === step.id ? renderInlineAddForm(_showInlineForm.type, step.id) : ''}

            ${wsInProgress ? `<div style="margin-top:12px;text-align:right">
                ${ExpUI.actionButton({ label: '🚩 Flag', variant: 'ghost', size: 'sm', title: 'Flag for cross-module attention', onclick: `ExploreWorkshopDetailView.showInlineForm('flag','${step.id}')` })}
            </div>` : ''}
        </div>`;
    }

    function renderChildSection(title, colorClass, items, cardFn, formType, stepId, canAdd) {
        return `<div style="margin-top:12px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                <strong style="font-size:13px;color:var(--${colorClass})">${title} (${items.length})</strong>
                ${canAdd ? ExpUI.actionButton({ label: `+ ${title.replace(/s$/, '')}`, variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.showInlineForm('${formType}','${stepId}')` }) : ''}
            </div>
            ${items.map(i => cardFn(i)).join('') || `<p style="font-size:12px;color:var(--sap-text-secondary)">No ${title.toLowerCase()} yet</p>`}
        </div>`;
    }

    // ── Fit Decision Selector (only in_progress) ─────────────────────
    function renderFitDecisionSelector(step, currentFit) {
        const fits = ['fit', 'partial_fit', 'gap'];
        const labels = { fit: 'Fit', partial_fit: 'Partial Fit', gap: 'Gap' };
        return `<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f1f5f9">
            <span style="font-size:12px;font-weight:600;color:var(--sap-text-secondary)">Fit Decision:</span>
            ${fits.map(f => {
                const isActive = currentFit === f;
                return `<label style="display:inline-flex;align-items:center;gap:4px;cursor:pointer;padding:4px 10px;border-radius:var(--exp-radius-pill);background:${isActive ? fitColor(f) + '20' : '#f1f5f9'};border:2px solid ${isActive ? fitColor(f) : 'transparent'};font-size:12px;font-weight:600;color:${isActive ? fitColor(f) : 'var(--sap-text-secondary)'}">
                    <input type="radio" name="fitDecision_${step.id}" value="${f}" ${isActive ? 'checked' : ''} style="display:none"
                           onchange="ExploreWorkshopDetailView.setFitDecision('${step.id}','${f}')">
                    ${labels[f]}
                </label>`;
            }).join('')}
        </div>`;
    }

    function renderFitReadonly(fitStatus) {
        return `<div style="padding:4px 0;font-size:12px;color:var(--sap-text-secondary)">
            Fit Decision: ${ExpUI.fitBadge(fitStatus)}
        </div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // ITEM CARDS (reused in steps tab + list tabs)
    // ═══════════════════════════════════════════════════════════════════
    function renderDecisionCard(d) {
        return `<div class="exp-card" style="border-left:3px solid var(--exp-decision);padding:10px 14px;margin-bottom:6px">
            <div style="display:flex;align-items:flex-start;gap:8px">
                <div style="flex:1">
                    <div style="font-weight:600;font-size:13px">${esc(d.text || d.description || d.title || '')}</div>
                    <div style="font-size:11px;color:var(--sap-text-secondary);margin-top:4px">
                        ${d.decided_by ? `👤 ${esc(d.decided_by)}` : ''}
                        ${d.category ? ` · ${ExpUI.pill({ label: d.category, variant: 'decision', size: 'sm' })}` : ''}
                        ${d.status && d.status !== 'active' ? ` · ${ExpUI.pill({ label: d.status, variant: d.status === 'superseded' ? 'draft' : 'danger', size: 'sm' })}` : ''}
                    </div>
                </div>
                <code style="font-size:10px;color:var(--sap-text-secondary)">${esc(d.code || '')}</code>
            </div>
        </div>`;
    }

    function renderOpenItemCard(o) {
        const overdue = o.is_overdue || (o.due_date && new Date(o.due_date) < new Date() && !['closed', 'resolved'].includes(o.status));
        return `<div class="exp-card" style="border-left:3px solid var(--exp-open-item);padding:10px 14px;margin-bottom:6px">
            <div style="display:flex;align-items:flex-start;gap:8px">
                <div style="flex:1">
                    <div style="display:flex;align-items:center;gap:6px">
                        <code style="font-size:11px;color:var(--sap-text-secondary)">${esc(o.code || '')}</code>
                        ${ExpUI.priorityPill(o.priority)}
                        ${ExpUI.oiStatusPill(o.status)}
                        ${overdue ? `<span style="color:var(--exp-gap);font-size:11px;font-weight:700">⚠ OVERDUE${o.days_overdue ? ' (' + o.days_overdue + 'd)' : ''}</span>` : ''}
                    </div>
                    <div style="font-weight:500;font-size:13px;margin-top:4px">${esc(o.title || '')}</div>
                    <div style="font-size:11px;color:var(--sap-text-secondary);margin-top:4px">
                        ${o.assignee_name || o.assignee_id ? `👤 ${esc(o.assignee_name || o.assignee_id)}` : ''}
                        ${o.due_date ? ` · 📅 ${esc(o.due_date)}` : ''}
                    </div>
                </div>
                ${workshop().status === 'in_progress' ? renderOITransitionButtons(o) : ''}
            </div>
        </div>`;
    }

    function renderOITransitionButtons(o) {
        const actions = {
            open:        [{ label: 'Start', action: 'start_work' }],
            in_progress: [{ label: 'Resolve', action: 'resolve' }, { label: 'Block', action: 'block' }],
            blocked:     [{ label: 'Unblock', action: 'unblock' }],
        };
        const available = actions[o.status] || [];
        if (!available.length) return '';
        return `<div style="display:flex;gap:4px;flex-direction:column">${available.map(a =>
            ExpUI.actionButton({ label: a.label, variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.transitionOI('${o.id}','${a.action}')` })
        ).join('')}</div>`;
    }

    function renderRequirementCard(r) {
        return `<div class="exp-card" style="border-left:3px solid var(--exp-requirement);padding:10px 14px;margin-bottom:6px">
            <div style="display:flex;align-items:flex-start;gap:8px">
                <div style="flex:1">
                    <div style="display:flex;align-items:center;gap:6px">
                        <code style="font-size:11px;color:var(--sap-text-secondary)">${esc(r.code || '')}</code>
                        ${ExpUI.priorityPill(r.priority)}
                        ${r.type ? ExpUI.pill({ label: r.type.replace(/_/g, ' '), variant: 'info', size: 'sm' }) : ''}
                    </div>
                    <div style="font-weight:500;font-size:13px;margin-top:4px">${esc(r.title || '')}</div>
                    <div style="margin-top:6px">${ExpUI.statusFlowIndicator(r.status || 'draft')}</div>
                    ${r.backlog_item_id ? '<div style="font-size:11px;color:var(--exp-decision);margin-top:2px">⚙ WRICEF linked</div>' : r.config_item_id ? '<div style="font-size:11px;color:var(--exp-open-item);margin-top:2px">🔧 CFG linked</div>' : ''}
                    ${r.effort_hours ? `<div style="font-size:11px;color:var(--sap-text-secondary);margin-top:2px">Effort: ${esc(String(r.effort_hours))}h</div>` : ''}
                </div>
                ${renderReqActions(r)}
            </div>
        </div>`;
    }

    function renderReqActions(r) {
        const btns = [];
        const s = r.status || 'draft';
        const converted = !!(r.backlog_item_id || r.config_item_id);

        // Convert / Move to Backlog — based on BOTH status and convert state
        if (s === 'approved' && !converted) {
            btns.push(ExpUI.actionButton({ label: '⚙ Convert First', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.showConvertModal('${r.id}')` }));
        } else if (s === 'approved' && converted) {
            btns.push(ExpUI.actionButton({ label: 'Move to Backlog', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.transitionReq('${r.id}','push_to_alm')` }));
        } else if (s === 'in_backlog' && !converted) {
            btns.push(ExpUI.actionButton({ label: '⚙ Convert', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.showConvertModal('${r.id}')` }));
        }

        // Other available transitions (exclude push_to_alm — handled above)
        const avail = (r.available_transitions || []).filter(t => t !== 'push_to_alm');
        if (avail.length) {
            btns.push(...avail.slice(0, 2).map(t =>
                ExpUI.actionButton({ label: t.replace(/_/g, ' '), variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.transitionReq('${r.id}','${t}')` })
            ));
        }
        // Traceability view (WR-3.5)
        if (typeof TraceView !== 'undefined') {
            btns.push(ExpUI.actionButton({ label: '🔍 Trace', variant: 'ghost', size: 'sm', onclick: `TraceView.showForRequirement('${r.id}')` }));
        }
        if (!btns.length) return '';
        return `<div style="display:flex;gap:4px;flex-direction:column">${btns.join('')}</div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // INLINE ADD FORMS
    // ═══════════════════════════════════════════════════════════════════
    function renderInlineAddForm(type, stepId) {
        if (type === 'flag') return renderFlagForm(stepId);

        const forms = {
            decision: `<div class="exp-inline-form" style="margin-top:12px">
                <h4 style="margin-bottom:8px;color:var(--exp-decision)">New Decision</h4>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Decision Text</label><textarea id="inlineDecText" rows="2" placeholder="What was decided?"></textarea></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Decided By</label><input id="inlineDecBy" type="text" placeholder="Name"></div>
                    <div class="exp-inline-form__field"><label>Category</label>
                        <select id="inlineDecCat"><option value="process">Process</option><option value="configuration">Configuration</option><option value="customization">Customization</option><option value="integration">Integration</option><option value="other">Other</option></select>
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
                        <select id="inlineOIPriority"><option value="P1">P1 - Critical</option><option value="P2" selected>P2 - High</option><option value="P3">P3 - Medium</option><option value="P4">P4 - Low</option></select>
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
                        <select id="inlineReqPriority"><option value="P1">P1</option><option value="P2" selected>P2</option><option value="P3">P3</option><option value="P4">P4</option></select>
                    </div>
                    <div class="exp-inline-form__field"><label>Type</label>
                        <select id="inlineReqType"><option value="configuration">Configuration</option><option value="functional">Functional</option><option value="enhancement">Enhancement</option><option value="integration">Integration</option><option value="report">Report</option><option value="migration">Migration</option></select>
                    </div>
                    <div class="exp-inline-form__field"><label>Effort (hours)</label><input id="inlineReqEffort" type="number" min="0" step="1" placeholder="0"></div>
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

    // ── Cross-Module Flag Form (BUG-5 fix) ───────────────────────────
    function renderFlagForm(stepId) {
        return `<div class="exp-inline-form" style="margin-top:12px">
            <h4 style="margin-bottom:8px;color:var(--exp-gap)">🚩 Cross-Module Flag</h4>
            <div class="exp-inline-form__row">
                <div class="exp-inline-form__field"><label>Target Process Area</label><input id="inlineFlagArea" type="text" placeholder="e.g. MM, FI, SD" maxlength="5"></div>
                <div class="exp-inline-form__field"><label>Target Scope Item</label><input id="inlineFlagScope" type="text" placeholder="Optional scope item code"></div>
            </div>
            <div class="exp-inline-form__row">
                <div class="exp-inline-form__field"><label>Description</label><textarea id="inlineFlagDesc" rows="2" placeholder="What needs attention from the other module?"></textarea></div>
            </div>
            <div class="exp-inline-form__actions">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', size: 'sm', onclick: 'ExploreWorkshopDetailView.hideInlineForm()' })}
                ${ExpUI.actionButton({ label: 'Raise Flag', variant: 'warning', size: 'sm', onclick: `ExploreWorkshopDetailView.submitInlineForm('flag','${stepId}')` })}
            </div>
        </div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // LIST TABS (Decisions, Open Items, Requirements)
    // ═══════════════════════════════════════════════════════════════════
    function renderDecisionsTab() {
        const decs = decisions();
        if (!decs.length) return emptyTab('decisions', '💬');
        return `<table class="exp-table">
            <thead><tr><th>Code</th><th>Decision</th><th>Category</th><th>Decided By</th><th>Status</th><th>Step</th></tr></thead>
            <tbody>${decs.map(d => {
                const step = steps().find(s => s.id === d.process_step_id);
                return `<tr>
                    <td><code>${esc(d.code || '')}</code></td>
                    <td>${esc(d.text || d.description || '')}</td>
                    <td>${d.category ? ExpUI.pill({ label: d.category, variant: 'decision', size: 'sm' }) : '—'}</td>
                    <td>${esc(d.decided_by || '')}</td>
                    <td>${d.status ? ExpUI.pill({ label: d.status, variant: d.status === 'active' ? 'success' : 'draft', size: 'sm' }) : ''}</td>
                    <td style="font-size:11px">${esc(step?.name || step?.code || '')}</td>
                </tr>`;
            }).join('')}</tbody>
        </table>`;
    }

    function renderOpenItemsTab() {
        const ois = openItems();
        if (!ois.length) return emptyTab('open items', '⚠️');
        return `<table class="exp-table">
            <thead><tr><th>Code</th><th>Title</th><th>Priority</th><th>Status</th><th>Assignee</th><th>Due Date</th><th></th></tr></thead>
            <tbody>${ois.map(o => {
                const overdue = o.is_overdue;
                return `<tr>
                    <td><code>${esc(o.code || '')}</code></td>
                    <td>${esc(o.title || '')}</td>
                    <td>${ExpUI.priorityPill(o.priority)}</td>
                    <td>${ExpUI.oiStatusPill(o.status)}</td>
                    <td>${esc(o.assignee_name || o.assignee_id || '—')}</td>
                    <td style="color:${overdue ? 'var(--exp-gap)' : 'inherit'};font-weight:${overdue ? '700' : 'normal'}">${esc(o.due_date || '—')}${overdue ? ' ⚠' : ''}</td>
                    <td>${renderOITransitionButtons(o)}</td>
                </tr>`;
            }).join('')}</tbody>
        </table>`;
    }

    function renderRequirementsTab() {
        const reqs = requirements();
        if (!reqs.length) return emptyTab('requirements', '📝');
        return `<table class="exp-table">
            <thead><tr><th>Code</th><th>Title</th><th>Type</th><th>Priority</th><th>Status</th><th>Complexity</th><th></th></tr></thead>
            <tbody>${reqs.map(r => `<tr>
                <td><code>${esc(r.code || '')}</code></td>
                <td>${esc(r.title || '')}</td>
                <td>${r.type ? ExpUI.pill({ label: r.type.replace(/_/g, ' '), variant: 'info', size: 'sm' }) : '—'}</td>
                <td>${ExpUI.priorityPill(r.priority)}</td>
                <td>${ExpUI.statusFlowIndicator(r.status || 'draft')}</td>
                <td>${esc(r.complexity || '—')}</td>
                <td>${renderReqActions(r)}</td>
            </tr>`).join('')}</tbody>
        </table>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // AGENDA TAB
    // ═══════════════════════════════════════════════════════════════════
    function renderAgendaTab() {
        const items = agendaItems();
        if (!items.length) {
            return renderAgendaCRUD() + emptyTab('agenda items', '📋');
        }
        const sorted = [...items].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
        return renderAgendaCRUD() + `<div class="exp-timeline">
            ${sorted.map(a => {
                const timeStr = a.time ? (typeof a.time === 'string' ? a.time.substring(0, 5) : a.time) : '';
                return `<div class="exp-timeline__item">
                    <div class="exp-timeline__time">${esc(timeStr)}</div>
                    <div class="exp-timeline__content" style="display:flex;justify-content:space-between;align-items:flex-start">
                        <div>
                            <strong>${esc(a.title || '')}</strong>
                            <span style="font-size:11px;color:var(--sap-text-secondary);margin-left:8px">${a.duration_minutes ? a.duration_minutes + ' min' : ''}</span>
                            ${a.type ? ` · ${ExpUI.pill({ label: a.type, variant: 'info', size: 'sm' })}` : ''}
                            ${a.notes ? `<div style="font-size:12px;color:var(--sap-text-secondary);margin-top:2px">${esc(a.notes)}</div>` : ''}
                        </div>
                        <div style="display:flex;gap:4px">
                            ${ExpUI.actionButton({ label: '✏', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.editAgendaItem('${a.id}')` })}
                            ${ExpUI.actionButton({ label: '🗑', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.deleteAgendaItem('${a.id}')` })}
                        </div>
                    </div>
                </div>`;
            }).join('')}
        </div>`;
    }

    function renderAgendaCRUD() {
        return `<div style="margin-bottom:12px">
            ${ExpUI.actionButton({ label: '+ Add Agenda Item', variant: 'primary', size: 'sm', onclick: 'ExploreWorkshopDetailView.showAgendaForm()' })}
        </div>
        <div id="agendaFormContainer"></div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // ATTENDEES TAB
    // ═══════════════════════════════════════════════════════════════════
    function renderAttendeesTab() {
        const atts = attendees();
        return `<div style="margin-bottom:12px">
            ${ExpUI.actionButton({ label: '+ Add Attendee', variant: 'primary', size: 'sm', onclick: 'ExploreWorkshopDetailView.showAttendeeForm()' })}
        </div>
        <div id="attendeeFormContainer"></div>
        ${!atts.length ? emptyTab('attendees', '👥') : `<div style="display:flex;flex-direction:column">
            ${atts.map(a => `<div class="exp-attendee" style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f1f5f9">
                <div class="exp-attendee__avatar" style="width:36px;height:36px;border-radius:50%;background:var(--exp-l3);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px">${esc((a.name || '?').charAt(0).toUpperCase())}</div>
                <div style="flex:1">
                    <div style="font-weight:500;font-size:13px">${esc(a.name || '')}</div>
                    <div style="font-size:11px;color:var(--sap-text-secondary)">${esc(a.role || '')} ${a.organization ? `· ${esc(a.organization)}` : ''}</div>
                </div>
                <div>
                    ${a.attendance_status === 'confirmed' ? ExpUI.pill({ label: '✓ Confirmed', variant: 'success', size: 'sm' })
                     : a.attendance_status === 'tentative' ? ExpUI.pill({ label: '? Tentative', variant: 'warning', size: 'sm' })
                     : a.attendance_status === 'declined'  ? ExpUI.pill({ label: '✗ Declined', variant: 'danger', size: 'sm' })
                     : ExpUI.pill({ label: esc(a.attendance_status || 'invited'), variant: 'draft', size: 'sm' })}
                </div>
                <div style="display:flex;gap:4px">
                    ${ExpUI.actionButton({ label: '🗑', variant: 'ghost', size: 'sm', onclick: `ExploreWorkshopDetailView.deleteAttendee('${a.id}')` })}
                </div>
            </div>`).join('')}
        </div>`}`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // SESSIONS TAB (BUG-4 fix — now rendered)
    // ═══════════════════════════════════════════════════════════════════
    function renderSessionsTab() {
        const sess = sessions();
        if (!sess.length) return emptyTab('sessions', '📅');

        return `<div style="display:flex;flex-direction:column;gap:var(--exp-space-sm)">
            ${sess.map(s => {
                const isCurrent = s.id === _wsId;
                return `<div class="exp-card" style="border-left:3px solid ${isCurrent ? 'var(--exp-l3)' : '#e2e8f0'};${isCurrent ? 'background:#f0f9ff;' : ''}cursor:pointer"
                    onclick="${isCurrent ? '' : `localStorage.setItem('exp_selected_workshop','${s.id}');ExploreWorkshopDetailView.render()`}">
                    <div class="exp-card__body" style="display:flex;align-items:center;gap:12px">
                        <div style="font-size:20px;font-weight:700;color:var(--exp-l3);min-width:36px;text-align:center">${s.session_number || '?'}</div>
                        <div style="flex:1">
                            <div style="font-weight:500;font-size:13px">${esc(s.name || '')}</div>
                            <div style="font-size:11px;color:var(--sap-text-secondary)">
                                ${s.date ? `📅 ${esc(s.date)}` : ''}
                                ${s.start_time ? ` · 🕐 ${esc(s.start_time)}` : ''}
                                ${s.type ? ` · ${esc(s.type.replace(/_/g, ' '))}` : ''}
                            </div>
                        </div>
                        ${ExpUI.workshopStatusPill(s.status)}
                        ${isCurrent ? ExpUI.pill({ label: 'Current', variant: 'info', size: 'sm' }) : ''}
                    </div>
                </div>`;
            }).join('')}
        </div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // DOCUMENTS TAB
    // ═══════════════════════════════════════════════════════════════════
    function renderDocumentsTab() {
        const generateBtns = `<div style="display:flex;gap:8px;margin-bottom:16px">
            ${ExpUI.actionButton({ label: '📝 Meeting Minutes', variant: 'primary', onclick: "ExploreWorkshopDetailView.generateDoc('meeting_minutes')" })}
            ${ExpUI.actionButton({ label: '📊 Workshop Summary', variant: 'secondary', onclick: "ExploreWorkshopDetailView.generateDoc('workshop_summary')" })}
            ${ExpUI.actionButton({ label: '🔗 Traceability Report', variant: 'secondary', onclick: "ExploreWorkshopDetailView.generateDoc('traceability_report')" })}
        </div>`;

        if (!_documents.length) {
            return generateBtns + emptyTab('documents', '📄');
        }

        const rows = _documents.map(d => {
            const typeLabel = { meeting_minutes: '📝 Minutes', workshop_summary: '📊 Summary', traceability_report: '🔗 Traceability' }[d.type] || d.type;
            const dt = d.generated_at || d.created_at;
            return `<tr>
                <td>${esc(typeLabel)}</td>
                <td>${esc(d.title || '—')}</td>
                <td>${dt ? new Date(dt).toLocaleDateString() : '—'}</td>
                <td>${esc(d.generated_by || d.created_by || '—')}</td>
                <td>${ExpUI.actionButton({ label: 'View', variant: 'link', onclick: `ExploreWorkshopDetailView.viewDoc('${d.id}')` })}</td>
            </tr>`;
        }).join('');

        return generateBtns + `<table class="exp-table">
            <thead><tr><th>Type</th><th>Title</th><th>Generated</th><th>By</th><th></th></tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // L3 CONSOLIDATED DECISION
    // ═══════════════════════════════════════════════════════════════════
    function renderL3ConsolidatedDecision() {
        if (workshop().status !== 'completed') return '';
        const s = steps();
        const fitCounts = {
            fit:         s.filter(st => st.fit_decision === 'fit').length,
            partial_fit: s.filter(st => st.fit_decision === 'partial_fit').length,
            gap:         s.filter(st => st.fit_decision === 'gap').length,
            pending:     s.filter(st => !st.fit_decision || st.fit_decision === 'pending').length,
        };
        const total = Object.values(fitCounts).reduce((a, b) => a + b, 0);
        const suggested = total ? (fitCounts.gap > 0 ? 'gap' : fitCounts.partial_fit > 0 ? 'partial_fit' : 'fit') : 'pending';

        return `<div class="exp-card" style="margin-top:var(--exp-space-md);border:2px solid var(--exp-l3);border-radius:var(--exp-radius-lg)">
            <div class="exp-card__header" style="border-bottom:1px solid #e2e8f0"><h3 class="exp-card__title" style="color:var(--exp-l3)">L3 Consolidated Decision</h3></div>
            <div class="exp-card__body">
                <div style="margin-bottom:12px">
                    ${ExpUI.fitBarMini(fitCounts, { height: 10 })}
                    <div style="display:flex;gap:12px;margin-top:6px;font-size:12px">
                        <span style="color:var(--exp-fit)">● Fit ${fitCounts.fit}</span>
                        <span style="color:var(--exp-partial)">◐ Partial ${fitCounts.partial_fit}</span>
                        <span style="color:var(--exp-gap)">● Gap ${fitCounts.gap}</span>
                        <span style="color:var(--exp-pending)">○ Pending ${fitCounts.pending}</span>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
                    <span style="font-size:13px;font-weight:600">Suggestion:</span> ${ExpUI.fitBadge(suggested)}
                </div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Accept', variant: 'success', size: 'sm', onclick: `ExploreWorkshopDetailView.acceptL3Suggestion('${suggested}')` })}
                    ${ExpUI.actionButton({ label: 'Override', variant: 'warning', size: 'sm', onclick: 'ExploreWorkshopDetailView.overrideL3Decision()' })}
                </div>
            </div>
        </div>`;
    }

    function emptyTab(name, icon) {
        return `<div class="exp-empty"><div class="exp-empty__icon">${icon}</div><div class="exp-empty__title">No ${name} yet</div><p class="exp-empty__text">Items will appear here as they are added during the workshop.</p></div>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    // ACTIONS
    // ═══════════════════════════════════════════════════════════════════

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

    // ── setFitDecision (BUG-1 fix) ───────────────────────────────────
    async function setFitDecision(stepId, decision) {
        try {
            // Use POST /workshops/<id>/fit-decisions (bulk upsert endpoint)
            await ExploreAPI.fitDecisions.create(_pid, _wsId, {
                step_id: stepId,
                fit_decision: decision,
            });
            App.toast(`Fit → ${decision.replace(/_/g, ' ')}`, 'success');

            // Prompt for requirement on gap/partial
            if (decision === 'gap' || decision === 'partial_fit') {
                const step = steps().find(s => s.id === stepId);
                if (step && confirm(`Step "${step.name || step.code}" marked as ${decision.replace(/_/g, ' ')}.\n\nWould you like to create a requirement?`)) {
                    _showInlineForm = { type: 'requirement', stepId };
                }
            }

            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed to update fit decision', 'error');
        }
    }

    // ── toggleStepFlag (demo_shown, bpmn_reviewed) ───────────────────
    async function toggleStepFlag(stepId, field, value) {
        try {
            await ExploreAPI.processSteps.update(stepId, { [field]: value });
        } catch (err) {
            App.toast(err.message || 'Update failed', 'error');
            await fetchAll();
            renderPage();
        }
    }

    // ── submitInlineForm (BUG-2 fix — uses processSteps.addX) ────────
    async function submitInlineForm(type, stepId) {
        if (_inlineBusy) return;
        _lastScrollY = window.scrollY;
        try {
            _inlineBusy = true;

            // 1. Read form values while DOM is alive
            let payload = {};
            if (type === 'decision') {
                const text = document.getElementById('inlineDecText')?.value?.trim();
                const decidedBy = document.getElementById('inlineDecBy')?.value?.trim();
                if (!text || !decidedBy) { App.toast('Text and decided by are required', 'error'); return; }
                payload = { text, decided_by: decidedBy, category: document.getElementById('inlineDecCat')?.value };
            } else if (type === 'openItem') {
                const title = document.getElementById('inlineOITitle')?.value?.trim();
                if (!title) { App.toast('Title is required', 'error'); return; }
                payload = {
                    title,
                    priority: document.getElementById('inlineOIPriority')?.value,
                    assignee_name: document.getElementById('inlineOIAssignee')?.value,
                    due_date: document.getElementById('inlineOIDue')?.value || null,
                    description: document.getElementById('inlineOIDesc')?.value,
                };
            } else if (type === 'requirement') {
                const title = document.getElementById('inlineReqTitle')?.value?.trim();
                if (!title) { App.toast('Title is required', 'error'); return; }
                payload = {
                    title,
                    priority: document.getElementById('inlineReqPriority')?.value,
                    type: document.getElementById('inlineReqType')?.value,
                    effort_hours: parseFloat(document.getElementById('inlineReqEffort')?.value) || null,
                    description: document.getElementById('inlineReqDesc')?.value,
                };
            } else if (type === 'flag') {
                // BUG-5 fix: actually create cross-module flag
                const area = document.getElementById('inlineFlagArea')?.value?.trim();
                const desc = document.getElementById('inlineFlagDesc')?.value?.trim();
                if (!area || !desc) { App.toast('Target area and description are required', 'error'); return; }
                payload = {
                    target_process_area: area.toUpperCase(),
                    target_scope_item_code: document.getElementById('inlineFlagScope')?.value?.trim() || null,
                    description: desc,
                };
            }

            // 2. Hide form
            _showInlineForm = null;
            renderPage();

            // 3. API call — all routed through processSteps namespace (BUG-2 fix)
            if (type === 'decision') {
                await ExploreAPI.processSteps.addDecision(stepId, payload);
            } else if (type === 'openItem') {
                await ExploreAPI.processSteps.addOpenItem(stepId, payload);
            } else if (type === 'requirement') {
                await ExploreAPI.processSteps.addRequirement(stepId, payload);
            } else if (type === 'flag') {
                await ExploreAPI.crossModuleFlags.create(stepId, payload);
            }

            const label = type === 'openItem' ? 'Open item' : type === 'flag' ? 'Flag' : type.charAt(0).toUpperCase() + type.slice(1);
            App.toast(`${label} created`, 'success');
            await fetchAll();
            renderPage();
            setTimeout(() => window.scrollTo(0, _lastScrollY), 0);
        } catch (err) {
            App.toast(err.message || 'Creation failed', 'error');
        } finally {
            _inlineBusy = false;
        }
    }

    // ── Workshop Lifecycle Transitions (BUG-6, BUG-7 fixes) ──────────
    async function startWorkshop() {
        if (!confirm('Start this workshop? Process steps will be created from scope items.')) return;
        try {
            const result = await ExploreAPI.workshops.start(_pid, _wsId);
            if (result.warnings && result.warnings.length) {
                result.warnings.forEach(w => App.toast(w, 'warning'));
            }
            App.toast(`Workshop started — ${result.steps_created || 0} step(s) created`, 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed to start workshop', 'error');
        }
    }

    async function completeWorkshop() {
        try {
            const result = await ExploreAPI.workshops.complete(_pid, _wsId);
            if (result.warnings && result.warnings.length) {
                App.toast(`Workshop completed with warnings:\n• ${result.warnings.join('\n• ')}`, 'warning');
            } else {
                App.toast('Workshop completed', 'success');
            }
            await fetchAll();
            renderPage();
        } catch (err) {
            // If 400 due to unassessed steps, offer force option
            if (err.message && err.message.includes('not yet assessed')) {
                if (confirm(`${err.message}\n\nForce complete anyway?`)) {
                    try {
                        const result = await API.post(`/explore/workshops/${_wsId}/complete`, { force: true });
                        App.toast('Workshop force-completed', 'warning');
                        await fetchAll();
                        renderPage();
                    } catch (e2) {
                        App.toast(e2.message || 'Force complete failed', 'error');
                    }
                }
            } else {
                App.toast(err.message || 'Failed to complete workshop', 'error');
            }
        }
    }

    // BUG-7 fix: prompt for mandatory reason
    async function reopenWorkshop() {
        const reason = prompt('Reason for reopening this workshop (required):');
        if (!reason || !reason.trim()) {
            App.toast('Reopen reason is required', 'warning');
            return;
        }
        try {
            await ExploreAPI.workshops.reopen(_pid, _wsId, { reason: reason.trim() });
            App.toast('Workshop reopened', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed to reopen workshop', 'error');
        }
    }

    // BUG-6 fix: use correct createDelta endpoint
    async function createDeltaWorkshop() {
        if (!confirm('Create a delta design workshop based on this completed workshop?')) return;
        try {
            const result = await ExploreAPI.workshops.createDelta(_pid, _wsId);
            const delta = result.delta_workshop || result;
            App.toast(`Delta workshop ${delta.code || ''} created`, 'success');
            // Navigate to the new delta workshop
            if (delta.id) {
                localStorage.setItem('exp_selected_workshop', delta.id);
                await render();
            }
        } catch (err) {
            App.toast(err.message || 'Failed to create delta', 'error');
        }
    }

    // ── OI Transition ────────────────────────────────────────────────
    async function transitionOI(oiId, action) {
        try {
            await ExploreAPI.openItems.transition(_pid, oiId, { action });
            App.toast(`Open item → ${action.replace(/_/g, ' ')}`, 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Transition failed', 'error');
        }
    }

    // ── Requirement Transition + Convert ─────────────────────────────
    async function transitionReq(reqId, action) {
        try {
            await ExploreAPI.requirements.transition(_pid, reqId, { action, project_id: _pid });
            App.toast(`Requirement → ${action.replace(/_/g, ' ')}`, 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Transition failed', 'error');
        }
    }

    function showConvertModal(reqId) {
        const r = requirements().find(x => x.id === reqId);
        if (!r) return;

        const html = `<div class="modal-content" style="max-width:480px;padding:24px">
            <h2 style="margin-bottom:4px">Convert Requirement</h2>
            <p style="font-size:13px;color:var(--sap-text-secondary);margin-bottom:16px">
                <code>${esc(r.code || '')}</code> — ${esc(r.title || '')}
            </p>
            <div class="exp-inline-form">
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Target Type</label>
                        <select id="wsConvertTargetType" onchange="document.getElementById('wsConvertWricefRow').style.display = this.value === 'backlog' ? 'flex' : 'none'">
                            <option value="">Auto-detect</option>
                            <option value="backlog" selected>WRICEF (Backlog Item)</option>
                            <option value="config">Configuration Item</option>
                        </select>
                    </div>
                </div>
                <div class="exp-inline-form__row" id="wsConvertWricefRow">
                    <div class="exp-inline-form__field"><label>WRICEF Type</label>
                        <select id="wsConvertWricefType">
                            <option value="">Auto-detect from title</option>
                            <option value="enhancement">Enhancement (E)</option>
                            <option value="report">Report (R)</option>
                            <option value="interface">Interface (I)</option>
                            <option value="conversion">Conversion (C)</option>
                            <option value="workflow">Workflow (W)</option>
                            <option value="form">Form (F)</option>
                        </select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Module Override</label>
                        <select id="wsConvertModule">${typeof SAPConstants !== 'undefined' ? SAPConstants.moduleOptionsHTML(r.sap_module || r.process_area || '') : '<option value="">—</option>'}</select>
                    </div>
                </div>
            </div>
            <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: '⚙ Convert', variant: 'primary', onclick: `ExploreWorkshopDetailView.submitConvert('${reqId}')` })}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function submitConvert(reqId) {
        try {
            const data = {};
            const target = document.getElementById('wsConvertTargetType')?.value;
            const wricef = document.getElementById('wsConvertWricefType')?.value;
            const mod    = document.getElementById('wsConvertModule')?.value?.trim();

            if (target) data.target_type = target;
            if (wricef) data.wricef_type = wricef;
            if (mod)    data.module = mod;

            const result = await ExploreAPI.requirements.convert(_pid, reqId, data);
            App.closeModal();

            const label = result.config_item_id
                ? `Config item #${result.config_item_id} created`
                : `WRICEF backlog item #${result.backlog_item_id} created`;
            App.toast(label, result.status === 'already_converted' ? 'info' : 'success');

            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Conversion failed', 'error');
        }
    }

    // ── L3 Sign-off Actions ──────────────────────────────────────────
    async function acceptL3Suggestion(status) {
        const firstStep = steps()[0];
        const l3Id = firstStep?.parent_id;
        if (!l3Id) { App.toast('No L3 scope item found', 'warning'); return; }
        try {
            await ExploreAPI.signoff.performL3(_pid, l3Id, { suggested_status: status });
            App.toast('L3 suggestion accepted', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed', 'error');
        }
    }

    function overrideL3Decision() {
        const firstStep = steps()[0];
        const l3Id = firstStep?.parent_id;
        if (l3Id && typeof ExploreHierarchyView !== 'undefined') {
            ExploreHierarchyView.openSignOffDialog(l3Id, true);
        }
    }

    // ── Agenda CRUD ──────────────────────────────────────────────────
    function showAgendaForm() {
        const container = document.getElementById('agendaFormContainer');
        if (!container) return;
        container.innerHTML = `<div class="exp-inline-form" style="margin-bottom:16px">
            <div class="exp-inline-form__row">
                <div class="exp-inline-form__field"><label>Time</label><input id="agendaTime" type="time" required></div>
                <div class="exp-inline-form__field"><label>Title</label><input id="agendaTitle" type="text" placeholder="Agenda item title" required></div>
                <div class="exp-inline-form__field"><label>Duration (min)</label><input id="agendaDuration" type="number" min="5" step="5" value="30"></div>
                <div class="exp-inline-form__field"><label>Type</label>
                    <select id="agendaType"><option value="session">Session</option><option value="break">Break</option><option value="demo">Demo</option><option value="review">Review</option></select>
                </div>
            </div>
            <div class="exp-inline-form__actions">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', size: 'sm', onclick: `document.getElementById('agendaFormContainer').innerHTML=''` })}
                ${ExpUI.actionButton({ label: 'Add', variant: 'primary', size: 'sm', onclick: 'ExploreWorkshopDetailView.saveAgendaItem()' })}
            </div>
        </div>`;
    }

    async function saveAgendaItem() {
        const time = document.getElementById('agendaTime')?.value;
        const title = document.getElementById('agendaTitle')?.value?.trim();
        if (!time || !title) { App.toast('Time and title are required', 'error'); return; }
        try {
            await ExploreAPI.agenda.create(_pid, _wsId, {
                time,
                title,
                duration_minutes: parseInt(document.getElementById('agendaDuration')?.value) || 30,
                type: document.getElementById('agendaType')?.value || 'session',
            });
            App.toast('Agenda item added', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed', 'error');
        }
    }

    function editAgendaItem(itemId) {
        App.toast('Edit feature: delete and re-add the item', 'info');
    }

    async function deleteAgendaItem(itemId) {
        if (!confirm('Delete this agenda item?')) return;
        try {
            await ExploreAPI.agenda.delete(_pid, _wsId, itemId);
            App.toast('Deleted', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Delete failed', 'error');
        }
    }

    // ── Attendee CRUD ────────────────────────────────────────────────
    function showAttendeeForm() {
        const container = document.getElementById('attendeeFormContainer');
        if (!container) return;
        container.innerHTML = `<div class="exp-inline-form" style="margin-bottom:16px">
            <div class="exp-inline-form__row">
                <div class="exp-inline-form__field"><label>Name</label><input id="attName" type="text" placeholder="Full name" required></div>
                <div class="exp-inline-form__field"><label>Role</label><input id="attRole" type="text" placeholder="e.g. Consultant"></div>
                <div class="exp-inline-form__field"><label>Organization</label>
                    <select id="attOrg"><option value="customer">Customer</option><option value="partner">Partner</option><option value="sap">SAP</option></select>
                </div>
            </div>
            <div class="exp-inline-form__actions">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', size: 'sm', onclick: `document.getElementById('attendeeFormContainer').innerHTML=''` })}
                ${ExpUI.actionButton({ label: 'Add', variant: 'primary', size: 'sm', onclick: 'ExploreWorkshopDetailView.saveAttendee()' })}
            </div>
        </div>`;
    }

    async function saveAttendee() {
        const name = document.getElementById('attName')?.value?.trim();
        if (!name) { App.toast('Name is required', 'error'); return; }
        try {
            await ExploreAPI.attendees.create(_pid, _wsId, {
                name,
                role: document.getElementById('attRole')?.value?.trim(),
                organization: document.getElementById('attOrg')?.value || 'customer',
            });
            App.toast('Attendee added', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed', 'error');
        }
    }

    async function deleteAttendee(attId) {
        if (!confirm('Remove this attendee?')) return;
        try {
            await ExploreAPI.attendees.delete(_pid, _wsId, attId);
            App.toast('Removed', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Delete failed', 'error');
        }
    }

    // ── Document Actions ─────────────────────────────────────────────
    async function generateDoc(docType) {
        try {
            App.toast('Generating document…', 'info');
            const doc = await ExploreAPI.documents.generate(_pid, _wsId, { type: docType });
            App.toast(`${doc.title || 'Document'} generated`, 'success');
            _documents.unshift(doc);
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Generation failed', 'error');
        }
    }

    function viewDoc(docId) {
        const doc = _documents.find(d => d.id === docId);
        if (!doc) return;

        let html = esc(doc.content || 'No content')
            .replace(/^### (.+)$/gm, '<h4>$1</h4>')
            .replace(/^## (.+)$/gm, '<h3>$1</h3>')
            .replace(/^# (.+)$/gm, '<h2>$1</h2>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
            .replace(/\n/g, '<br>');

        App.openModal(`
            <div class="exp-card" style="max-height:70vh;overflow-y:auto;padding:20px">
                <div class="exp-card__header" style="display:flex;justify-content:space-between;align-items:center">
                    <span>${esc(doc.title || 'Document')}</span>
                    ${ExpUI.actionButton({ label: 'Close', variant: 'secondary', onclick: 'App.closeModal()' })}
                </div>
                <div class="exp-card__body" style="font-size:13px;line-height:1.6">${html}</div>
            </div>
        `);
    }

    // ═══════════════════════════════════════════════════════════════════
    // MAIN RENDER
    // ═══════════════════════════════════════════════════════════════════
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
            case 'sessions':     tabContent = renderSessionsTab(); break;
            case 'documents':    tabContent = renderDocumentsTab(); break;
        }

        main.innerHTML = `<div class="explore-page">
            ${typeof DemoFlow !== 'undefined' && DemoFlow.isActive() ? DemoFlow.breadcrumbHTML() : ''}
            ${renderHeader()}
            ${renderKPIStrip()}
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
        if (!_wsId) { App.navigate('explore-workshops'); return; }

        // Reset state
        _activeTab = 'steps';
        _expandedStepId = null;
        _showInlineForm = null;
        _inlineBusy = false;
        _documents = [];

        main.innerHTML = `<div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:300px">
            <div style="text-align:center;color:var(--sap-text-secondary)"><div style="font-size:28px;margin-bottom:8px">⏳</div>Loading workshop…</div>
        </div>`;

        try {
            await fetchAll();
            if (!_ws || !workshop().id) {
                main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Workshop not found</div></div>`;
                return;
            }
            renderPage();
        } catch (err) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ═══════════════════════════════════════════════════════════════════
    return {
        render,
        setTab,
        toggleStep,
        showInlineForm,
        hideInlineForm,
        submitInlineForm,
        setFitDecision,
        toggleStepFlag,
        startWorkshop,
        completeWorkshop,
        reopenWorkshop,
        createDeltaWorkshop,
        transitionOI,
        transitionReq,
        showConvertModal,
        submitConvert,
        acceptL3Suggestion,
        overrideL3Decision,
        showAgendaForm,
        saveAgendaItem,
        editAgendaItem,
        deleteAgendaItem,
        showAttendeeForm,
        saveAttendee,
        deleteAttendee,
        generateDoc,
        viewDoc,
    };
})();