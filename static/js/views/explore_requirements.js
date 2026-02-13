/**
 * Explore Phase — Module D: Requirement & Open Item Hub
 * F-031: RequirementHubPage   F-032: RequirementKpiStrip
 * F-033: RequirementRow       F-034: RequirementExpandedDetail
 * F-035: StatusFlowIndicator  F-036: RequirementActionButtons
 * F-037: RequirementFilterBar F-038: OpenItemKpiStrip
 * F-039: OpenItemRow          F-040: OpenItemExpandedDetail
 * F-041: OverdueToggle        F-042: AssigneeDropdown
 *
 * Route: /explore/requirements (via App.navigate)
 */
const ExploreRequirementHubView = (() => {
    'use strict';

    const esc = ExpUI.esc;

    // ── State ────────────────────────────────────────────────────────
    let _pid = null;
    let _activeTab = 'requirements';   // requirements | openItems
    let _requirements = [];
    let _openItems = [];
    let _reqStats = {};
    let _oiStats = {};
    let _expandedId = null;

    // Requirement filters
    let _reqFilters = { search: '', status: '', priority: '', type: '', area: '' };
    let _reqSort = { key: 'code', dir: 'asc' };

    // Open item filters
    let _oiFilters = { search: '', status: '', priority: '', assignee: '', overdue: false };
    let _oiSort = { key: 'code', dir: 'asc' };

    // ── API ──────────────────────────────────────────────────────────
    async function fetchAll() {
        const [reqs, ois, reqStats, oiStats] = await Promise.allSettled([
            ExploreAPI.requirements.list(_pid),
            ExploreAPI.openItems.list(_pid),
            ExploreAPI.requirements.stats(_pid),
            ExploreAPI.openItems.stats(_pid),
        ]);
        _requirements = reqs.status === 'fulfilled' ? (reqs.value || []) : [];
        _openItems = ois.status === 'fulfilled' ? (ois.value || []) : [];
        _reqStats = reqStats.status === 'fulfilled' ? (reqStats.value || {}) : {};
        _oiStats = oiStats.status === 'fulfilled' ? (oiStats.value || {}) : {};
    }

    // ── Requirement KPI Strip (F-032) ────────────────────────────────
    function renderReqKpiStrip() {
        const total = _requirements.length;
        const p1 = _requirements.filter(r => r.priority === 'P1').length;
        const draft = _requirements.filter(r => r.status === 'draft').length;
        const review = _requirements.filter(r => r.status === 'under_review').length;
        const approved = _requirements.filter(r => r.status === 'approved').length;
        const backlog = _requirements.filter(r => r.status === 'in_backlog').length;
        const realized = _requirements.filter(r => r.status === 'realized').length;
        const totalEffort = _requirements.reduce((s, r) => s + (r.effort_hours || r.estimated_effort || 0), 0);

        return `<div class="exp-kpi-strip">
            ${ExpUI.kpiBlock({ value: total, label: 'Requirements', accent: 'var(--exp-requirement)' })}
            ${ExpUI.kpiBlock({ value: p1, label: 'P1 Critical', accent: 'var(--exp-gap)' })}
            ${ExpUI.kpiBlock({ value: approved, label: 'Approved', accent: 'var(--exp-fit)' })}
            ${ExpUI.kpiBlock({ value: backlog, label: 'In Backlog', accent: '#3b82f6' })}
            ${ExpUI.kpiBlock({ value: totalEffort, label: 'Effort (days)', accent: '#64748b' })}
            ${(() => { const n = _requirements.filter(r => r.status === 'approved' && !r.backlog_item_id && !r.config_item_id).length; return n > 0 ? `<div style="margin-left:auto">${ExpUI.actionButton({ label: '⚙ Batch Convert (' + n + ')', variant: 'ghost', size: 'sm', onclick: 'ExploreRequirementHubView.batchConvert()' })}</div>` : ''; })()}
        </div>
        ${ExpUI.metricBar({
            label: 'Status Distribution',
            total: total || 1,
            segments: [
                {value: draft, label: 'Draft', color: '#94a3b8'},
                {value: review, label: 'Review', color: '#f59e0b'},
                {value: approved, label: 'Approved', color: 'var(--exp-fit)'},
                {value: backlog, label: 'Backlog', color: '#3b82f6'},
                {value: realized, label: 'Realized', color: 'var(--exp-decision)'},
            ],
        })}`;
    }

    // ── Requirement Filter Bar (F-037) ───────────────────────────────
    function renderReqFilterBar() {
        return ExpUI.filterBar({
            id: 'requirementsFB',
            searchPlaceholder: 'Search requirements…',
            searchValue: _reqFilters.search,
            onSearch: "ExploreRequirementHubView.setReqFilter('search',this.value)",
            onChange: "ExploreRequirementHubView.onReqFilterBarChange",
            filters: [
                {
                    id: 'status', label: 'Status', icon: '📌', type: 'single',
                    color: 'var(--exp-fit)',
                    options: [
                        ...ExpUI.REQ_STATUSES.map(s => ({ value: s, label: s.replace(/_/g, ' ') })),
                        { value: 'deferred', label: 'Deferred' },
                        { value: 'rejected', label: 'Rejected' },
                    ],
                    selected: _reqFilters.status || '',
                },
                {
                    id: 'priority', label: 'Priority', icon: '🔥', type: 'single',
                    color: 'var(--exp-gap)',
                    options: [
                        { value: 'P1', label: 'P1' }, { value: 'P2', label: 'P2' },
                        { value: 'P3', label: 'P3' }, { value: 'P4', label: 'P4' },
                    ],
                    selected: _reqFilters.priority || '',
                },
                {
                    id: 'type', label: 'Type', icon: '🧩', type: 'single',
                    color: 'var(--exp-requirement)',
                    options: [
                        { value: 'functional', label: 'Functional' },
                        { value: 'enhancement', label: 'Enhancement' },
                        { value: 'custom_development', label: 'Custom Dev' },
                        { value: 'integration', label: 'Integration' },
                        { value: 'report', label: 'Report' },
                    ],
                    selected: _reqFilters.type || '',
                },
            ],
            actionsHtml: `
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                    ${ExpUI.actionButton({ label: '+ New Requirement', variant: 'primary', size: 'sm', onclick: 'ExploreRequirementHubView.createRequirement()' })}
                </div>
            `,
        });
    }

    // ── Requirement Row (F-033) + Expanded Detail (F-034) ────────────
    function renderRequirementTable() {
        const filtered = getFilteredReqs();
        if (!filtered.length) {
            return `<div class="exp-empty"><div class="exp-empty__icon">📝</div><div class="exp-empty__title">No requirements found</div></div>`;
        }

        const sortIcon = (k) => _reqSort.key === k ? (_reqSort.dir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
        const th = (label, key) => `<th onclick="ExploreRequirementHubView.sortReq('${key}')">${label}<span class="sort-icon${_reqSort.key === key ? ' sort-icon--active' : ''}">${sortIcon(key)}</span></th>`;

        const header = `<thead><tr>
            <th style="width:20px"></th>
            ${th('ID','code')} ${th('Priority','priority')} <th>Type</th> <th>Fit</th>
            ${th('Title','title')} <th>Scope</th> <th>Area</th> <th>Effort</th> <th>Status</th> <th>Backlog</th> <th>ALM</th>
        </tr></thead>`;

        const rows = filtered.map(r => {
            const isExpanded = _expandedId === r.id;
            return `<tr class="exp-expandable-row" onclick="ExploreRequirementHubView.toggleExpand('${r.id}')">
                <td><span class="exp-expandable-row__chevron${isExpanded ? ' exp-expandable-row__chevron--open' : ''}">▶</span></td>
                <td><code style="font-family:var(--exp-font-mono);font-size:11px">${esc(r.code || '')}</code></td>
                <td>${ExpUI.priorityPill(r.priority)}</td>
                <td>${r.requirement_type ? ExpUI.pill({ label: r.requirement_type, variant: 'info', size: 'sm' }) : '—'}</td>
                <td>${ExpUI.fitBadge(r.fit_status || r.fit_gap_status || 'pending', { compact: true })}</td>
                <td class="exp-truncate" style="max-width:200px">${esc(r.title || '')}</td>
                <td style="font-size:12px">${esc(r.scope_item_name || r.scope_item_code || '')}</td>
                <td>${ExpUI.areaPill(r.process_area || r.area || r.area_code || '')}</td>
                <td style="font-size:12px">${(r.effort_hours || r.estimated_effort) ? (r.effort_hours || r.estimated_effort) + 'd' : '—'}</td>
                <td>${ExpUI.statusFlowIndicator(r.status || 'draft')}</td>
                <td>${r.backlog_item_id ? '<span title="WRICEF item linked" style="color:var(--exp-decision);font-size:12px">⚙ WRICEF</span>' : r.config_item_id ? '<span title="Config item linked" style="color:var(--exp-open-item);font-size:12px">🔧 CFG</span>' : '—'}</td>
                <td>${(r.alm_id || r.cloud_alm_id) ? '<span title="Synced to ALM">🔗</span>' : '—'}</td>
            </tr>
            ${isExpanded ? `<tr><td colspan="12" style="padding:0">${renderReqExpandedDetail(r)}</td></tr>` : ''}`;
        }).join('');

        return `<div class="exp-card"><div class="exp-card__body" style="overflow-x:auto">
            <table class="exp-table">${header}<tbody>${rows}</tbody></table>
        </div></div>`;
    }

    // ── Requirement Expanded Detail (F-034) ──────────────────────────
    function renderReqExpandedDetail(r) {
        return `<div class="exp-expandable-detail" onclick="event.stopPropagation()">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                <div>
                    <div class="exp-detail-section__title">Traceability</div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Workshop</span><span class="exp-detail-row__value">${esc(r.workshop_code || '—')}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Scope Item</span><span class="exp-detail-row__value">${esc(r.scope_item_name || r.scope_item_code || '—')}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Process Step</span><span class="exp-detail-row__value">${esc(r.l4_code || '—')}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Created By</span><span class="exp-detail-row__value">${esc(r.created_by_name || r.created_by_id || r.created_by || '—')}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Approved By</span><span class="exp-detail-row__value">${esc(r.approved_by_name || r.approved_by_id || r.approved_by || '—')}</span></div>
                </div>
                <div>
                    <div class="exp-detail-section__title">Links</div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Backlog Item</span><span class="exp-detail-row__value">${r.backlog_item_id ? `⚙ WRICEF #${r.backlog_item_id}` : r.config_item_id ? `🔧 CFG #${r.config_item_id}` : '—'}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">ALM ID</span><span class="exp-detail-row__value">${esc(r.alm_id || r.cloud_alm_id || '—')}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Linked OIs</span><span class="exp-detail-row__value">${r.linked_open_items ? r.linked_open_items.length : 0}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Dependencies</span><span class="exp-detail-row__value">${r.dependencies ? r.dependencies.length : 0}</span></div>
                    ${r.description ? `<div style="margin-top:8px"><div class="exp-detail-section__title">Description</div><p style="font-size:13px">${esc(r.description)}</p></div>` : ''}
                </div>
            </div>
            <div style="display:flex;gap:8px;margin-top:12px;padding-top:12px;border-top:1px solid #e2e8f0">
                ${renderReqActionButtons(r)}
            </div>
        </div>`;
    }

    // ── Requirement Action Buttons (F-036) ───────────────────────────
    function renderReqActionButtons(r) {
        const actions = [];
        const s = r.status || 'draft';

        if (s === 'draft') {
            actions.push(ExpUI.actionButton({ label: 'Submit for Review', variant: 'primary', size: 'sm', onclick: `ExploreRequirementHubView.transitionReq('${r.id}','submit_for_review')` }));
        }
        if (s === 'under_review') {
            actions.push(ExpUI.actionButton({ label: 'Approve', variant: 'success', size: 'sm', onclick: `ExploreRequirementHubView.transitionReq('${r.id}','approve')` }));
            actions.push(ExpUI.actionButton({ label: 'Reject', variant: 'danger', size: 'sm', onclick: `ExploreRequirementHubView.transitionReq('${r.id}','reject')` }));
        }
        if (s === 'approved') {
            if (r.backlog_item_id || r.config_item_id) {
                // Already converted — allow move to backlog
                actions.push(ExpUI.actionButton({ label: 'Move to Backlog', variant: 'primary', size: 'sm', onclick: `ExploreRequirementHubView.transitionReq('${r.id}','push_to_alm')` }));
            } else {
                // ADR-1: Must convert first
                actions.push(ExpUI.actionButton({ label: '⚙ Convert First', variant: 'primary', size: 'sm', onclick: `ExploreRequirementHubView.showConvertModal('${r.id}')` }));
            }
        }
        if (s === 'in_backlog') {
            actions.push(ExpUI.actionButton({ label: 'Realize', variant: 'success', size: 'sm', onclick: `ExploreRequirementHubView.transitionReq('${r.id}','mark_realized')` }));
            if (!r.backlog_item_id && !r.config_item_id) {
                actions.push(ExpUI.actionButton({ label: '⚙ Convert', variant: 'ghost', size: 'sm', onclick: `ExploreRequirementHubView.showConvertModal('${r.id}')` }));
            }
        }
        if (s === 'realized') {
            actions.push(ExpUI.actionButton({ label: 'Verify', variant: 'success', size: 'sm', onclick: `ExploreRequirementHubView.transitionReq('${r.id}','verify')` }));
        }
        // Defer: only valid from draft or approved per REQUIREMENT_TRANSITIONS
        if (s === 'draft' || s === 'approved') {
            actions.push(ExpUI.actionButton({ label: 'Defer', variant: 'secondary', size: 'sm', onclick: `ExploreRequirementHubView.transitionReq('${r.id}','defer')` }));
        }
        // Reactivate: only from deferred
        if (s === 'deferred') {
            actions.push(ExpUI.actionButton({ label: 'Reactivate', variant: 'secondary', size: 'sm', onclick: `ExploreRequirementHubView.transitionReq('${r.id}','reactivate')` }));
        }
        if (!r.cloud_alm_id && (s === 'approved' || s === 'in_backlog')) {
            actions.push(ExpUI.actionButton({ label: '🔗 Push to ALM', variant: 'ghost', size: 'sm', onclick: `ExploreRequirementHubView.pushToALM('${r.id}')` }));
        }
        // Traceability view (WR-3.5)
        if (typeof TraceView !== 'undefined') {
            actions.push(ExpUI.actionButton({ label: '🔍 Trace', variant: 'ghost', size: 'sm', onclick: `TraceView.showForRequirement('${r.id}')` }));
        }

        return actions.join('');
    }

    // ── Status Flow Indicator (F-035) — delegated to ExpUI ─────────
    // (Already implemented in explore-shared.js as ExpUI.statusFlowIndicator)

    // ── Open Item KPI Strip (F-038) ──────────────────────────────────
    function renderOiKpiStrip() {
        const total = _openItems.length;
        const open = _openItems.filter(o => o.status === 'open').length;
        const inProg = _openItems.filter(o => o.status === 'in_progress').length;
        const blocked = _openItems.filter(o => o.status === 'blocked').length;
        const closed = _openItems.filter(o => o.status === 'closed' || o.status === 'resolved').length;
        const overdue = _openItems.filter(o => o.due_date && new Date(o.due_date) < new Date() && o.status !== 'closed' && o.status !== 'resolved').length;
        const p1Open = _openItems.filter(o => o.priority === 'P1' && o.status !== 'closed' && o.status !== 'resolved').length;

        return `<div class="exp-kpi-strip">
            ${ExpUI.kpiBlock({ value: total, label: 'Open Items', accent: 'var(--exp-open-item)' })}
            ${ExpUI.kpiBlock({ value: open, label: 'Open', accent: '#3b82f6' })}
            ${ExpUI.kpiBlock({ value: overdue, label: 'Overdue', accent: 'var(--exp-gap)' })}
            ${ExpUI.kpiBlock({ value: p1Open, label: 'P1 Open', accent: 'var(--exp-p1)' })}
        </div>
        ${ExpUI.metricBar({
            label: 'Status Distribution',
            total: total || 1,
            segments: [
                {value: open, label: 'Open', color: '#3b82f6'},
                {value: inProg, label: 'In Progress', color: '#f59e0b'},
                {value: blocked, label: 'Blocked', color: 'var(--exp-gap)'},
                {value: closed, label: 'Closed', color: 'var(--exp-fit)'},
            ],
        })}`;
    }

    // ── Open Item Filter Bar (F-041 OverdueToggle + F-042 AssigneeDropdown) ──
    function renderOiFilterBar() {
        const assignees = [...new Set(_openItems.map(o => o.assignee_name || o.assignee_id || o.assignee).filter(Boolean))].sort();
        return ExpUI.filterBar({
            id: 'openItemsFB',
            searchPlaceholder: 'Search open items…',
            searchValue: _oiFilters.search,
            onSearch: "ExploreRequirementHubView.setOiFilter('search',this.value)",
            onChange: "ExploreRequirementHubView.onOiFilterBarChange",
            filters: [
                {
                    id: 'status', label: 'Status', icon: '📌', type: 'single',
                    color: 'var(--exp-open-item)',
                    options: [
                        { value: 'open', label: 'Open' },
                        { value: 'in_progress', label: 'In Progress' },
                        { value: 'blocked', label: 'Blocked' },
                        { value: 'resolved', label: 'Resolved' },
                        { value: 'closed', label: 'Closed' },
                    ],
                    selected: _oiFilters.status || '',
                },
                {
                    id: 'priority', label: 'Priority', icon: '🔥', type: 'single',
                    color: 'var(--exp-gap)',
                    options: [
                        { value: 'P1', label: 'P1' }, { value: 'P2', label: 'P2' },
                        { value: 'P3', label: 'P3' }, { value: 'P4', label: 'P4' },
                    ],
                    selected: _oiFilters.priority || '',
                },
                {
                    id: 'assignee', label: 'Assignee', icon: '👤', type: 'single',
                    color: 'var(--exp-requirement)',
                    options: assignees.map(a => ({ value: a, label: a })),
                    selected: _oiFilters.assignee || '',
                },
                {
                    id: 'overdue', label: 'Overdue', icon: '🔴', type: 'single',
                    color: 'var(--exp-gap)',
                    options: [{ value: 'true', label: 'Overdue only' }],
                    selected: _oiFilters.overdue ? 'true' : '',
                },
            ],
            actionsHtml: `
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                    ${ExpUI.actionButton({ label: '+ New Open Item', variant: 'primary', size: 'sm', onclick: 'ExploreRequirementHubView.createOpenItem()' })}
                </div>
            `,
        });
    }

    // ── Open Item Row (F-039) + Expanded Detail (F-040) ──────────────
    function renderOpenItemTable() {
        const filtered = getFilteredOIs();
        if (!filtered.length) {
            return `<div class="exp-empty"><div class="exp-empty__icon">⚠️</div><div class="exp-empty__title">No open items found</div></div>`;
        }

        const sortIcon = (k) => _oiSort.key === k ? (_oiSort.dir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
        const th = (label, key) => `<th onclick="ExploreRequirementHubView.sortOi('${key}')">${label}<span class="sort-icon${_oiSort.key === key ? ' sort-icon--active' : ''}">${sortIcon(key)}</span></th>`;

        const header = `<thead><tr>
            <th style="width:20px"></th>
            ${th('ID','code')} ${th('Priority','priority')} <th>Status</th> <th>Category</th>
            ${th('Title','title')} ${th('Assignee','assignee')} ${th('Due Date','due_date')} <th>Area</th>
        </tr></thead>`;

        const rows = filtered.map(o => {
            const isExpanded = _expandedId === o.id;
            const overdue = o.due_date && new Date(o.due_date) < new Date() && o.status !== 'closed' && o.status !== 'resolved';
            return `<tr class="exp-expandable-row" onclick="ExploreRequirementHubView.toggleExpand('${o.id}')">
                <td><span class="exp-expandable-row__chevron${isExpanded ? ' exp-expandable-row__chevron--open' : ''}">▶</span></td>
                <td><code style="font-family:var(--exp-font-mono);font-size:11px">${esc(o.code || '')}</code></td>
                <td>${ExpUI.priorityPill(o.priority)}</td>
                <td>${ExpUI.oiStatusPill(o.status)}</td>
                <td>${o.category ? ExpUI.pill({ label: o.category, variant: 'draft', size: 'sm' }) : '—'}</td>
                <td class="exp-truncate" style="max-width:200px">${esc(o.title || '')}</td>
                <td style="font-size:12px">${esc(o.assignee_name || o.assignee_id || o.assignee || '—')}</td>
                <td style="font-size:12px;color:${overdue ? 'var(--exp-gap)' : 'inherit'};font-weight:${overdue ? '700' : 'normal'}">${o.due_date ? esc(o.due_date) : '—'}${overdue ? ' ⚠' : ''}</td>
                <td>${ExpUI.areaPill(o.process_area || o.area || o.area_code || '')}</td>
            </tr>
            ${isExpanded ? `<tr><td colspan="9" style="padding:0">${renderOiExpandedDetail(o)}</td></tr>` : ''}`;
        }).join('');

        return `<div class="exp-card"><div class="exp-card__body" style="overflow-x:auto">
            <table class="exp-table">${header}<tbody>${rows}</tbody></table>
        </div></div>`;
    }

    // ── Open Item Expanded Detail (F-040) ────────────────────────────
    function renderOiExpandedDetail(o) {
        return `<div class="exp-expandable-detail" onclick="event.stopPropagation()">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                <div>
                    <div class="exp-detail-section__title">Details</div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Workshop</span><span class="exp-detail-row__value">${esc(o.workshop_code || '—')}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Process Step</span><span class="exp-detail-row__value">${esc(o.l4_code || '—')}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Created By</span><span class="exp-detail-row__value">${esc(o.created_by_id || o.created_by || '—')}</span></div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Resolution</span><span class="exp-detail-row__value">${esc(o.resolution || '—')}</span></div>
                </div>
                <div>
                    <div class="exp-detail-section__title">Links</div>
                    <div class="exp-detail-row"><span class="exp-detail-row__label">Linked REQs</span><span class="exp-detail-row__value">${o.linked_requirements ? o.linked_requirements.length : 0}</span></div>
                    ${o.description ? `<div style="margin-top:8px"><div class="exp-detail-section__title">Description</div><p style="font-size:13px">${esc(o.description)}</p></div>` : ''}
                </div>
            </div>
            <div style="display:flex;gap:8px;margin-top:12px;padding-top:12px;border-top:1px solid #e2e8f0">
                ${renderOiActionButtons(o)}
            </div>
        </div>`;
    }

    function renderOiActionButtons(o) {
        const actions = [];
        const s = o.status || 'open';
        if (s === 'open') {
            actions.push(ExpUI.actionButton({ label: 'Start Progress', variant: 'primary', size: 'sm', onclick: `ExploreRequirementHubView.transitionOi('${o.id}','start_progress')` }));
            actions.push(ExpUI.actionButton({ label: 'Block', variant: 'danger', size: 'sm', onclick: `ExploreRequirementHubView.transitionOi('${o.id}','block')` }));
        }
        if (s === 'in_progress') {
            actions.push(ExpUI.actionButton({ label: 'Resolve', variant: 'success', size: 'sm', onclick: `ExploreRequirementHubView.transitionOi('${o.id}','resolve')` }));
            actions.push(ExpUI.actionButton({ label: 'Block', variant: 'danger', size: 'sm', onclick: `ExploreRequirementHubView.transitionOi('${o.id}','block')` }));
        }
        if (s === 'blocked') {
            actions.push(ExpUI.actionButton({ label: 'Unblock', variant: 'warning', size: 'sm', onclick: `ExploreRequirementHubView.transitionOi('${o.id}','unblock')` }));
        }
        if (s === 'resolved') {
            actions.push(ExpUI.actionButton({ label: 'Close', variant: 'success', size: 'sm', onclick: `ExploreRequirementHubView.transitionOi('${o.id}','close')` }));
        }
        return actions.join('');
    }

    // ── Filter Logic ─────────────────────────────────────────────────
    function getFilteredReqs() {
        let list = [..._requirements];
        const f = _reqFilters;
        if (f.search) {
            const q = f.search.toLowerCase();
            list = list.filter(r => (r.code||'').toLowerCase().includes(q) || (r.title||'').toLowerCase().includes(q));
        }
        if (f.status) list = list.filter(r => r.status === f.status);
        if (f.priority) list = list.filter(r => r.priority === f.priority);
        if (f.type) list = list.filter(r => r.requirement_type === f.type);
        if (f.area) list = list.filter(r => (r.area || r.area_code) === f.area);

        list.sort((a, b) => {
            let va = a[_reqSort.key] ?? '', vb = b[_reqSort.key] ?? '';
            if (typeof va === 'string') va = va.toLowerCase();
            if (typeof vb === 'string') vb = vb.toLowerCase();
            return _reqSort.dir === 'asc' ? (va < vb ? -1 : va > vb ? 1 : 0) : (va > vb ? -1 : va < vb ? 1 : 0);
        });
        return list;
    }

    function getFilteredOIs() {
        let list = [..._openItems];
        const f = _oiFilters;
        if (f.search) {
            const q = f.search.toLowerCase();
            list = list.filter(o => (o.code||'').toLowerCase().includes(q) || (o.title||'').toLowerCase().includes(q));
        }
        if (f.status) list = list.filter(o => o.status === f.status);
        if (f.priority) list = list.filter(o => o.priority === f.priority);
        if (f.assignee) list = list.filter(o => (o.assignee_name || o.assignee_id || o.assignee) === f.assignee);
        if (f.overdue) list = list.filter(o => o.due_date && new Date(o.due_date) < new Date() && o.status !== 'closed' && o.status !== 'resolved');

        list.sort((a, b) => {
            let va = a[_oiSort.key] ?? '', vb = b[_oiSort.key] ?? '';
            if (typeof va === 'string') va = va.toLowerCase();
            if (typeof vb === 'string') vb = vb.toLowerCase();
            return _oiSort.dir === 'asc' ? (va < vb ? -1 : va > vb ? 1 : 0) : (va > vb ? -1 : va < vb ? 1 : 0);
        });
        return list;
    }

    // ── Create Dialogs ───────────────────────────────────────────────
    async function createRequirement() {
        // Fetch L3 scope items for dropdown
        let l3Options = '<option value="">— Select L3 Scope Item —</option>';
        try {
            const l3Items = await ExploreAPI.levels.listL3(_pid);
            const items = Array.isArray(l3Items) ? l3Items : (l3Items.items || []);
            l3Options += items.map(p =>
                `<option value="${p.id}">${p.code || p.sap_code || ''} — ${p.name || ''}</option>`
            ).join('');
        } catch (e) {
            console.warn('Failed to load L3 items:', e);
        }

        const html = `<div class="modal-content" style="max-width:560px;padding:24px">
            <h2 style="margin-bottom:16px">Create Requirement</h2>
            <div class="exp-inline-form">
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Title</label><input id="newReqTitle" type="text" placeholder="Requirement title"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field" style="flex:2">
                        <label>L3 Scope Item <span style="color:var(--sap-error)">*</span></label>
                        <select id="newReqScopeItem" required>${l3Options}</select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Priority</label>
                        <select id="newReqPriority"><option value="P1">P1</option><option value="P2">P2</option><option value="P3" selected>P3</option><option value="P4">P4</option></select>
                    </div>
                    <div class="exp-inline-form__field"><label>Type</label>
                        <select id="newReqType"><option value="functional">Functional</option><option value="enhancement">Enhancement</option><option value="custom_development">Custom Dev</option><option value="integration">Integration</option><option value="report">Report</option></select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Effort (days)</label><input id="newReqEffort" type="number" min="0" step="0.5" placeholder="0"></div>
                    <div class="exp-inline-form__field"><label>Area (SAP Module)</label>
                        <select id="newReqArea">${SAPConstants.moduleOptionsHTML()}</select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Description</label><textarea id="newReqDesc" rows="3" placeholder="Details"></textarea></div>
                </div>
            </div>
            <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Create', variant: 'primary', onclick: 'ExploreRequirementHubView.submitCreateReq()' })}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function submitCreateReq() {
        try {
            const scopeItemId = document.getElementById('newReqScopeItem')?.value;
            if (!scopeItemId) {
                App.toast('L3 Scope Item is required', 'error');
                return;
            }
            await ExploreAPI.requirements.create(_pid, {
                title: document.getElementById('newReqTitle')?.value,
                scope_item_id: scopeItemId,
                priority: document.getElementById('newReqPriority')?.value,
                requirement_type: document.getElementById('newReqType')?.value,
                estimated_effort: parseFloat(document.getElementById('newReqEffort')?.value) || null,
                area_code: document.getElementById('newReqArea')?.value || null,
                description: document.getElementById('newReqDesc')?.value || null,
            });
            App.closeModal();
            App.toast('Requirement created', 'success');
            await fetchAll();
            renderPage();
        } catch (err) { App.toast(err.message || 'Failed', 'error'); }
    }

    function createOpenItem() {
        const html = `<div class="modal-content" style="max-width:560px;padding:24px">
            <h2 style="margin-bottom:16px">Create Open Item</h2>
            <div class="exp-inline-form">
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Title</label><input id="newOiTitle" type="text" placeholder="Open item title"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Priority</label>
                        <select id="newOiPriority"><option value="P1">P1</option><option value="P2">P2</option><option value="P3" selected>P3</option><option value="P4">P4</option></select>
                    </div>
                    <div class="exp-inline-form__field"><label>Assignee</label><input id="newOiAssignee" type="text" placeholder="Name"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Due Date</label><input id="newOiDue" type="date"></div>
                    <div class="exp-inline-form__field"><label>Category</label>
                        <select id="newOiCat"><option value="process">Process</option><option value="technical">Technical</option><option value="data">Data</option><option value="integration">Integration</option><option value="other">Other</option></select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Description</label><textarea id="newOiDesc" rows="3" placeholder="Details"></textarea></div>
                </div>
            </div>
            <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Create', variant: 'primary', onclick: 'ExploreRequirementHubView.submitCreateOi()' })}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function submitCreateOi() {
        try {
            await ExploreAPI.openItems.create(_pid, {
                title: document.getElementById('newOiTitle')?.value,
                priority: document.getElementById('newOiPriority')?.value,
                assignee: document.getElementById('newOiAssignee')?.value || null,
                due_date: document.getElementById('newOiDue')?.value || null,
                category: document.getElementById('newOiCat')?.value || null,
                description: document.getElementById('newOiDesc')?.value || null,
            });
            App.closeModal();
            App.toast('Open item created', 'success');
            await fetchAll();
            renderPage();
        } catch (err) { App.toast(err.message || 'Failed', 'error'); }
    }

    // ── Convert Modal (W-4) ─────────────────────────────────────────
    function showConvertModal(reqId) {
        const r = _requirements.find(x => x.id === reqId);
        if (!r) return;

        const html = `<div class="modal-content" style="max-width:480px;padding:24px">
            <h2 style="margin-bottom:4px">Convert Requirement</h2>
            <p style="font-size:13px;color:var(--sap-text-secondary);margin-bottom:16px">
                <code>${esc(r.code)}</code> — ${esc(r.title)}
            </p>
            <div class="exp-inline-form">
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Target Type</label>
                        <select id="convertTargetType" onchange="document.getElementById('convertWricefRow').style.display = this.value === 'backlog' ? 'flex' : 'none'">
                            <option value="">Auto-detect</option>
                            <option value="backlog" selected>WRICEF (Backlog Item)</option>
                            <option value="config">Configuration Item</option>
                        </select>
                    </div>
                </div>
                <div class="exp-inline-form__row" id="convertWricefRow">
                    <div class="exp-inline-form__field"><label>WRICEF Type</label>
                        <select id="convertWricefType">
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
                        <select id="convertModule">${SAPConstants.moduleOptionsHTML(r.sap_module || r.process_area || '')}</select>
                    </div>
                </div>
            </div>
            <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: '⚙ Convert', variant: 'primary', onclick: `ExploreRequirementHubView.submitConvert('${reqId}')` })}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function submitConvert(reqId) {
        try {
            const data = {};
            const target = document.getElementById('convertTargetType')?.value;
            const wricef = document.getElementById('convertWricefType')?.value;
            const mod    = document.getElementById('convertModule')?.value?.trim();

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

    async function batchConvert() {
        const approvedNoLink = _requirements.filter(r =>
            (r.status === 'approved') && !r.backlog_item_id && !r.config_item_id
        );
        if (!approvedNoLink.length) {
            App.toast('No approved requirements to convert', 'info');
            return;
        }
        if (!confirm(`Convert ${approvedNoLink.length} approved requirement(s) to backlog items?\n\nThis will auto-detect WRICEF/Config type for each.`)) return;

        try {
            const ids = approvedNoLink.map(r => r.id);
            const result = await ExploreAPI.requirements.batchConvert(_pid, { requirement_ids: ids });
            const sc = (result.success || []).length;
            const ec = (result.errors || []).length;
            App.toast(`Converted: ${sc}, Errors: ${ec}`, ec ? 'warning' : 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Batch conversion failed', 'error');
        }
    }

    // ── Transition Actions ───────────────────────────────────────────
    async function transitionReq(id, action) {
        try {
            await ExploreAPI.requirements.transition(_pid, id, { action });
            App.toast(`Requirement ${action}ed`, 'success');
            await fetchAll();
            renderPage();
        } catch (err) { App.toast(err.message || 'Transition failed', 'error'); }
    }

    async function transitionOi(id, action) {
        try {
            await ExploreAPI.openItems.transition(_pid, id, { action });
            App.toast(`Open item ${action}ed`, 'success');
            await fetchAll();
            renderPage();
        } catch (err) { App.toast(err.message || 'Transition failed', 'error'); }
    }

    async function pushToALM(id) {
        App.toast('Pushing to SAP Cloud ALM…', 'info');
        // Placeholder — actual implementation would call cloud_alm service
    }

    // ── Public Actions ───────────────────────────────────────────────
    function setTab(t) { _activeTab = t; _expandedId = null; renderPage(); }
    function toggleExpand(id) { _expandedId = _expandedId === id ? null : id; renderPage(); }
    function setReqFilter(key, val) { _reqFilters[key] = val || ''; renderPage(); }
    function setOiFilter(key, val) { _oiFilters[key] = val || ''; renderPage(); }
    function onReqFilterBarChange(update) {
        if (update._clearAll) {
            _reqFilters = { search: _reqFilters.search || '', status: '', priority: '', type: '', area: '' };
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    _reqFilters[key] = '';
                } else if (Array.isArray(val)) {
                    _reqFilters[key] = val[0];
                } else {
                    _reqFilters[key] = val;
                }
            });
        }
        renderPage();
    }
    function onOiFilterBarChange(update) {
        if (update._clearAll) {
            _oiFilters = { search: _oiFilters.search || '', status: '', priority: '', assignee: '', overdue: false };
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (key === 'overdue') {
                    _oiFilters.overdue = val === 'true';
                } else if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    _oiFilters[key] = '';
                } else if (Array.isArray(val)) {
                    _oiFilters[key] = val[0];
                } else {
                    _oiFilters[key] = val;
                }
            });
        }
        renderPage();
    }
    function toggleOverdue() { _oiFilters.overdue = !_oiFilters.overdue; renderPage(); }
    function sortReq(key) {
        if (_reqSort.key === key) _reqSort.dir = _reqSort.dir === 'asc' ? 'desc' : 'asc';
        else { _reqSort.key = key; _reqSort.dir = 'asc'; }
        renderPage();
    }
    function sortOi(key) {
        if (_oiSort.key === key) _oiSort.dir = _oiSort.dir === 'asc' ? 'desc' : 'asc';
        else { _oiSort.key = key; _oiSort.dir = 'asc'; }
        renderPage();
    }

    // ── Main Render (F-031) ──────────────────────────────────────────
    function renderPage() {
        const main = document.getElementById('mainContent');
        const isReqTab = _activeTab === 'requirements';

        main.innerHTML = `<div class="explore-page">
            ${typeof DemoFlow !== 'undefined' && DemoFlow.isActive() ? DemoFlow.breadcrumbHTML() : ''}
            <div class="explore-page__header">
                <div>
                    <h1 class="explore-page__title">Requirements & Open Items</h1>
                    <p class="explore-page__subtitle">Track, manage, and govern all explore-phase requirements and open items</p>
                </div>
            </div>
            <div class="exp-tabs" style="margin-bottom:var(--exp-space-lg)">
                <button class="exp-tab${isReqTab ? ' exp-tab--active' : ''}" onclick="ExploreRequirementHubView.setTab('requirements')">
                    Requirements ${ExpUI.countChip(_requirements.length)}
                </button>
                <button class="exp-tab${!isReqTab ? ' exp-tab--active' : ''}" onclick="ExploreRequirementHubView.setTab('openItems')">
                    Open Items ${ExpUI.countChip(_openItems.length)}
                </button>
            </div>
            ${isReqTab ? renderReqKpiStrip() : renderOiKpiStrip()}
            ${isReqTab ? renderReqFilterBar() : renderOiFilterBar()}
            ${isReqTab ? renderRequirementTable() : renderOpenItemTable()}
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
        main.innerHTML = `<div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:300px">
            <div style="text-align:center;color:var(--sap-text-secondary)"><div style="font-size:28px;margin-bottom:8px">⏳</div>Loading…</div>
        </div>`;
        try {
            await fetchAll();
            renderPage();
        } catch (err) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
        }
    }

    return {
        render, setTab, toggleExpand,
        setReqFilter, setOiFilter, onReqFilterBarChange, onOiFilterBarChange, toggleOverdue, sortReq, sortOi,
        transitionReq, transitionOi, pushToALM,
        createRequirement, submitCreateReq,
        createOpenItem, submitCreateOi,
        showConvertModal, submitConvert, batchConvert,
    };
})();
