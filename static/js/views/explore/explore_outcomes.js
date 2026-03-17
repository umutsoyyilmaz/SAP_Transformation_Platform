const ExploreOutcomeHubView = (() => {
    'use strict';

    const esc = ExpUI.esc;
    const OUTCOMES_WORKSPACE_KEY = 'pg.exploreOutcomesWorkspace';
    const REQUIREMENT_NAV_STATE_KEY = 'pg.exploreRequirementsNavState';

    let _pid = null;
    let _workspace = 'stream';
    let _streamTab = 'all';
    let _workshops = [];
    let _decisions = [];
    let _requirements = [];
    let _openItems = [];
    let _filters = { search: '', workshop: '', status: '', owner: '' };
    let _decisionFilters = { search: '', workshop: '', status: '', category: '', step: '' };
    let _stepsByWorkshop = {};
    let _stepsById = {};
    let _loadWarnings = [];
    let _pageTitle = 'Explore Outcomes';
    let _pageSubtitle = 'Single cockpit to manage workshop outputs, readiness, and downstream handoff.';
    let _breadcrumbLabel = 'Outcomes';
    let _pageTestId = 'explore-outcomes-page';

    function _persistWorkspaceState(state = {}) {
        try {
            sessionStorage.setItem(OUTCOMES_WORKSPACE_KEY, JSON.stringify(state));
        } catch {
            // Ignore storage failures; navigation will still work.
        }
    }

    function _consumeWorkspaceState() {
        try {
            const raw = sessionStorage.getItem(OUTCOMES_WORKSPACE_KEY);
            if (!raw) return null;
            sessionStorage.removeItem(OUTCOMES_WORKSPACE_KEY);
            return JSON.parse(raw);
        } catch {
            return null;
        }
    }

    function _peekRequirementRouteState() {
        try {
            const raw = sessionStorage.getItem(REQUIREMENT_NAV_STATE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }

    function _resolveRequirementRouteWorkspace() {
        const state = _peekRequirementRouteState();
        return state?.tab === 'openItems' ? 'openItems' : 'requirements';
    }

    function _selectWorkspace(workspace = 'stream', streamTab = '') {
        if (workspace === 'decisions') {
            _workspace = 'decisions';
            _streamTab = 'all';
            return;
        }
        if (workspace === 'requirements' || workspace === 'openItems' || workspace === 'handoff') {
            _workspace = workspace;
            return;
        }
        if (workspace === 'stream' && streamTab === 'decision') {
            _workspace = 'decisions';
            _streamTab = 'all';
            return;
        }
        _workspace = 'stream';
        _streamTab = streamTab === 'decision' ? 'decision' : 'all';
    }

    function _normalizeItems(payload) {
        if (Array.isArray(payload)) return payload;
        if (Array.isArray(payload?.items)) return payload.items;
        return [];
    }

    function _collectLoadWarning(label, error) {
        const message = error?.message || 'Request failed';
        const warning = `${label} could not be loaded: ${message}`;
        _loadWarnings.push(warning);
        console.warn(`[Explore Outcomes] ${warning}`, error);
    }

    async function fetchAll() {
        _loadWarnings = [];

        const [workshopsResult, requirementsResult, openItemsResult] = await Promise.allSettled([
            ExploreAPI.workshops.list(_pid),
            ExploreAPI.requirements.list(_pid),
            ExploreAPI.openItems.list(_pid),
        ]);

        if (workshopsResult.status === 'rejected') _collectLoadWarning('Workshops', workshopsResult.reason);
        if (requirementsResult.status === 'rejected') _collectLoadWarning('Requirements', requirementsResult.reason);
        if (openItemsResult.status === 'rejected') _collectLoadWarning('Open items', openItemsResult.reason);

        _workshops = workshopsResult.status === 'fulfilled' ? _normalizeItems(workshopsResult.value) : [];
        _requirements = requirementsResult.status === 'fulfilled' ? _normalizeItems(requirementsResult.value) : [];
        _openItems = openItemsResult.status === 'fulfilled' ? _normalizeItems(openItemsResult.value) : [];

        if (!_workshops.length && !_requirements.length && !_openItems.length && _loadWarnings.length) {
            throw new Error(_loadWarnings[0]);
        }

        const stepPayloads = await Promise.allSettled(
            _workshops.map((ws) => ExploreAPI.workshops.steps(_pid, ws.id))
        );
        _stepsByWorkshop = {};
        _stepsById = {};
        const failedStepLoads = stepPayloads.filter((result) => result.status === 'rejected').length;
        stepPayloads.forEach((result, index) => {
            const workshop = _workshops[index] || {};
            const items = result.status === 'fulfilled'
                ? (Array.isArray(result.value) ? result.value : (result.value?.items || []))
                : [];
            _stepsByWorkshop[workshop.id] = items;
            items.forEach((step) => {
                _stepsById[step.id] = {
                    ...step,
                    workshop_id: workshop.id,
                    workshop_name: workshop.name,
                    workshop_code: workshop.code,
                };
            });
        });
        if (failedStepLoads) {
            _loadWarnings.push(`${failedStepLoads} workshop step stream(s) could not be loaded.`);
        }

        const decisionPayloads = await Promise.allSettled(
            _workshops.map((ws) => ExploreAPI.decisions.list(_pid, ws.id))
        );
        const failedDecisionLoads = decisionPayloads.filter((result) => result.status === 'rejected').length;
        _decisions = decisionPayloads.flatMap((result, index) => {
            if (result.status !== 'fulfilled') return [];
            const workshop = _workshops[index] || {};
            const items = Array.isArray(result.value) ? result.value : (result.value?.items || []);
            return items.map((item) => {
                const step = _stepsById[item.process_step_id] || {};
                return {
                    ...item,
                    workshop_id: workshop.id,
                    workshop_name: workshop.name,
                    workshop_code: workshop.code,
                    process_step_name: step.name || item.process_step_name || '',
                    process_step_code: step.code || step.sap_code || item.process_step_code || '',
                    process_area_code: step.process_area_code || step.process_area || item.process_area_code || '',
                };
            });
        });
        if (failedDecisionLoads) {
            _loadWarnings.push(`${failedDecisionLoads} workshop decision stream(s) could not be loaded.`);
        }
    }

    function normalizedOutcomes() {
        const decisions = _decisions.map((item) => ({
            id: `decision-${item.id}`,
            kind: 'decision',
            title: item.title || item.summary || item.decision_text || 'Decision',
            subtitle: item.decision_text || item.notes || '',
            status: item.status || 'recorded',
            owner: item.owner_name || item.owner || item.decided_by || '',
            workshop: item.workshop_name || item.workshop_code || 'Unassigned workshop',
            trace: item.process_step_code || item.process_step_name || item.scope_item_code || '',
        }));
        const openItems = _openItems.map((item) => ({
            id: `oi-${item.id}`,
            kind: 'openItem',
            title: item.title || item.question || item.summary || 'Open Item',
            subtitle: item.description || item.resolution || '',
            status: item.status || 'open',
            owner: item.assignee_name || item.assignee || item.owner || '',
            workshop: item.workshop_name || item.workshop_code || 'Unassigned workshop',
            trace: item.process_step_code || item.process_step_name || item.scope_item_code || '',
        }));
        const requirements = _requirements.map((item) => ({
            id: `req-${item.id}`,
            kind: 'requirement',
            title: item.title || item.summary || item.code || 'Requirement',
            subtitle: item.description || '',
            status: item.status || 'draft',
            owner: item.created_by_name || item.owner || '',
            workshop: item.workshop_name || item.workshop_code || 'Unassigned workshop',
            trace: item.scope_item_name || item.scope_item_code || item.l4_code || '',
        }));
        return [...decisions, ...openItems, ...requirements];
    }

    function traceMetrics() {
        return {
            total: _requirements.length,
            linked: _requirements.filter((item) => item.backlog_item_id || item.config_item_id).length,
            ready: _requirements.filter((item) => item.status === 'approved' && !item.backlog_item_id && !item.config_item_id).length,
            blocked: _requirements.filter((item) => (item.linked_open_items || []).length > 0).length,
            unresolvedItems: _openItems.filter((item) => !['closed', 'resolved'].includes(item.status)).length,
        };
    }

    function workspaceMeta() {
        if (_workspace === 'decisions') {
            return {
                label: 'Decision Workspace',
                subtitle: 'Capture, revise, retire, and trace workshop decisions without dropping back into Workshop Detail.',
            };
        }
        if (_workspace === 'requirements') {
            return {
                label: 'Requirements Workspace',
                subtitle: 'Manage explore requirements, AI analysis, conversion readiness, and delivery handoff from the same cockpit.',
            };
        }
        if (_workspace === 'openItems') {
            return {
                label: 'Open Item Workspace',
                subtitle: 'Work unresolved questions, owner queues, blockers, and overdue items without leaving Outcomes.',
            };
        }
        if (_workspace === 'handoff') {
            return {
                label: 'Handoff Workspace',
                subtitle: 'Verify traceability, clear blockers, and convert approved requirements into backlog-ready delivery items.',
            };
        }
        if (_streamTab === 'decision') {
            return {
                label: 'Decision Stream',
                subtitle: 'Review workshop decisions in their operational context before they become requirements or open items.',
            };
        }
        return {
            label: 'Outcome Stream',
            subtitle: 'Single Explore cockpit for decisions, requirements, open items, and handoff readiness.',
        };
    }

    function matchesFilters(item) {
        if (_streamTab !== 'all' && item.kind !== _streamTab) return false;
        const q = (_filters.search || '').trim().toLowerCase();
        if (q) {
            const haystack = [item.title, item.subtitle, item.workshop, item.trace, item.owner].join(' ').toLowerCase();
            if (!haystack.includes(q)) return false;
        }
        if (_filters.workshop && item.workshop !== _filters.workshop) return false;
        if (_filters.status && item.status !== _filters.status) return false;
        if (_filters.owner) {
            const owner = (item.owner || '').toLowerCase();
            if (!owner.includes(_filters.owner.toLowerCase())) return false;
        }
        return true;
    }

    function statusTone(kind) {
        if (kind === 'decision') return 'var(--exp-decision)';
        if (kind === 'openItem') return 'var(--exp-open-item)';
        return 'var(--exp-requirement)';
    }

    function prettyKind(kind) {
        if (kind === 'openItem') return 'Open Item';
        return kind.charAt(0).toUpperCase() + kind.slice(1);
    }

    function renderHeader() {
        const meta = workspaceMeta();
        const total = normalizedOutcomes().length;
        const handoff = traceMetrics();

        return `<div class="explore-page__header">
            <div>
                <h1 class="explore-page__title">${esc(_pageTitle)}</h1>
                <p class="explore-page__subtitle">${esc(_pageSubtitle)}</p>
                <div style="margin-top:10px;display:grid;gap:4px">
                    <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--sap-text-secondary);font-weight:700">${esc(meta.label)}</div>
                    <div style="font-size:13px;color:var(--sap-text-secondary)">${esc(meta.subtitle)}</div>
                </div>
            </div>
            <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start">
                ${ExpUI.actionButton({ label: 'Workshop Hub', variant: 'secondary', onclick: "App.navigate('explore-workshops')" })}
                ${_workspace !== 'stream' || _streamTab !== 'all'
                    ? ExpUI.actionButton({ label: 'Open Stream', variant: 'ghost', onclick: "ExploreOutcomeHubView.navigateToWorkspace('stream')" })
                    : ''}
            </div>
        </div>
        <div class="exp-kpi-strip">
            ${ExpUI.kpiBlock({ value: total, label: 'Total Outcomes', accent: 'var(--exp-l2)' })}
            ${ExpUI.kpiBlock({ value: _decisions.length, label: 'Decisions', accent: 'var(--exp-decision)' })}
            ${ExpUI.kpiBlock({ value: _requirements.length, label: 'Requirements', accent: 'var(--exp-requirement)' })}
            ${ExpUI.kpiBlock({ value: handoff.unresolvedItems, label: 'Open Item Queue', accent: 'var(--exp-open-item)' })}
            ${ExpUI.kpiBlock({ value: handoff.ready, label: 'Ready for Handoff', accent: '#3b82f6' })}
        </div>`;
    }

    function renderStageNav() {
        return ExpUI.exploreStageNav({
            current: _pageTestId === 'explore-traceability-page' ? 'explore-traceability' : 'explore-outcomes',
        });
    }

    function renderLoadWarnings() {
        if (!_loadWarnings.length) return '';
        return `<div class="exp-card" style="margin-bottom:var(--exp-space-lg);border:1px solid rgba(245, 158, 11, 0.35);background:rgba(255, 247, 237, 0.96)">
            <div class="exp-card__body" style="padding:16px 18px">
                <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#9a3412;font-weight:700;margin-bottom:6px">Partial Data</div>
                <div style="font-weight:600;color:#7c2d12;margin-bottom:8px">Some outcome data could not be loaded.</div>
                <ul style="margin:0;padding-left:18px;color:#9a3412;font-size:13px;display:grid;gap:4px">
                    ${_loadWarnings.slice(0, 3).map((message) => `<li>${esc(message)}</li>`).join('')}
                </ul>
            </div>
        </div>`;
    }

    function renderWorkspaceTabs() {
        const handoff = traceMetrics();
        const isDecisionTab = _workspace === 'stream' && _streamTab === 'decision';
        const isStreamTab = _workspace === 'stream' && _streamTab === 'all';

        return `<div class="exp-tabs" style="margin-bottom:var(--exp-space-lg)">
            <button class="exp-tab${isStreamTab ? ' exp-tab--active' : ''}" onclick="ExploreOutcomeHubView.navigateToWorkspace('stream')">
                All Outcomes ${ExpUI.countChip(normalizedOutcomes().length)}
            </button>
            <button class="exp-tab${_workspace === 'decisions' || isDecisionTab ? ' exp-tab--active' : ''}" onclick="ExploreOutcomeHubView.navigateToWorkspace('decisions')">
                Decisions ${ExpUI.countChip(_decisions.length)}
            </button>
            <button class="exp-tab${_workspace === 'requirements' ? ' exp-tab--active' : ''}" onclick="ExploreOutcomeHubView.navigateToWorkspace('requirements')">
                Requirements ${ExpUI.countChip(_requirements.length)}
            </button>
            <button class="exp-tab${_workspace === 'openItems' ? ' exp-tab--active' : ''}" onclick="ExploreOutcomeHubView.navigateToWorkspace('openItems')">
                Open Items ${ExpUI.countChip(_openItems.length)}
            </button>
            <button class="exp-tab${_workspace === 'handoff' ? ' exp-tab--active' : ''}" onclick="ExploreOutcomeHubView.navigateToWorkspace('handoff')">
                Handoff ${ExpUI.countChip(handoff.total)}
            </button>
        </div>`;
    }

    function renderFilterBar() {
        const streamItems = normalizedOutcomes().filter((item) => _streamTab === 'all' || item.kind === _streamTab);
        const searchPlaceholder = _streamTab === 'decision' ? 'Search decisions...' : 'Search outcomes...';

        return ExpUI.filterBar({
            id: 'outcomesHubFilters',
            searchPlaceholder,
            searchValue: _filters.search,
            onSearch: "ExploreOutcomeHubView.setFilter('search', this.value)",
            onChange: 'ExploreOutcomeHubView.onFilterBarChange',
            filters: [
                {
                    id: 'workshop',
                    label: 'Workshop',
                    icon: '📋',
                    type: 'single',
                    color: 'var(--exp-l2)',
                    options: [...new Set(streamItems.map((item) => item.workshop).filter(Boolean))]
                        .sort()
                        .map((value) => ({ value, label: value })),
                    selected: _filters.workshop || '',
                },
                {
                    id: 'status',
                    label: 'Status',
                    icon: '📌',
                    type: 'single',
                    color: 'var(--exp-fit)',
                    options: [...new Set(streamItems.map((item) => item.status).filter(Boolean))]
                        .sort()
                        .map((value) => ({ value, label: value.replace(/_/g, ' ') })),
                    selected: _filters.status || '',
                },
            ],
            actionsHtml: `
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                    ${_streamTab === 'decision'
                        ? ExpUI.actionButton({ label: 'Capture in Workshops', variant: 'secondary', size: 'sm', onclick: "App.navigate('explore-workshops')" })
                        : ''}
                    ${ExpUI.actionButton({ label: '+ Decision', variant: 'secondary', size: 'sm', onclick: 'ExploreOutcomeHubView.openCreateDecision()' })}
                    ${ExpUI.actionButton({ label: '+ Requirement', variant: 'primary', size: 'sm', onclick: 'ExploreOutcomeHubView.openCreateRequirement()' })}
                    ${ExpUI.actionButton({ label: '+ Open Item', variant: 'secondary', size: 'sm', onclick: 'ExploreOutcomeHubView.openCreateOpenItem()' })}
                </div>
            `,
        });
    }

    function renderStreamList() {
        const items = normalizedOutcomes().filter(matchesFilters);
        if (!items.length) {
            return `<div class="exp-empty"><div class="exp-empty__icon">🧭</div><div class="exp-empty__title">No outcomes match the current filters</div></div>`;
        }
        return `<div class="explore-outcome-stack">
            ${items.map((item) => {
                let actionLabel = 'Open Workspace';
                let actionOnclick = "ExploreOutcomeHubView.navigateToWorkspace('stream')";
                if (item.kind === 'decision') {
                    actionLabel = 'Manage Decision';
                    actionOnclick = "ExploreOutcomeHubView.navigateToWorkspace('decisions')";
                } else if (item.kind === 'openItem') {
                    actionLabel = 'Open Queue';
                    actionOnclick = "ExploreOutcomeHubView.navigateToWorkspace('openItems')";
                } else if (item.status === 'approved' || item.status === 'in_backlog' || item.status === 'realized') {
                    actionLabel = 'Open Handoff';
                    actionOnclick = "ExploreOutcomeHubView.navigateToWorkspace('handoff')";
                } else {
                    actionLabel = 'Manage Requirement';
                    actionOnclick = "ExploreOutcomeHubView.navigateToWorkspace('requirements')";
                }

                return `
                    <div class="exp-card explore-outcome-card" data-kind="${item.kind}">
                        <div class="exp-card__body explore-outcome-card__body">
                            <div>
                                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px">
                                    ${ExpUI.pill({ label: prettyKind(item.kind), variant: 'info' })}
                                    ${ExpUI.pill({ label: item.status.replace(/_/g, ' '), variant: 'neutral' })}
                                </div>
                                <div style="font-weight:600;font-size:15px;margin-bottom:4px">${esc(item.title)}</div>
                                <div style="font-size:12px;color:var(--sap-text-secondary)">${esc(item.subtitle || 'No additional detail captured yet.')}</div>
                            </div>
                            <div style="font-size:12px;color:var(--sap-text-secondary);display:grid;gap:6px">
                                <div><strong style="color:var(--sap-text-primary)">Workshop:</strong> ${esc(item.workshop)}</div>
                                <div><strong style="color:var(--sap-text-primary)">Trace:</strong> ${esc(item.trace || 'Not linked')}</div>
                                <div><strong style="color:var(--sap-text-primary)">Owner:</strong> ${esc(item.owner || 'Unassigned')}</div>
                            </div>
                            <div style="border-left:3px solid ${statusTone(item.kind)};padding-left:12px;display:flex;align-items:center;min-height:100%">
                                <button class="btn btn-secondary btn-sm" onclick="${actionOnclick}">
                                    ${actionLabel}
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>`;
    }

    function getDecisionStep(decision) {
        return _stepsById[decision?.process_step_id] || {};
    }

    function getDecisionWorkshop(decision) {
        const step = getDecisionStep(decision);
        return _workshops.find((item) => item.id === decision?.workshop_id)
            || _workshops.find((item) => item.id === step.workshop_id)
            || null;
    }

    function getFilteredDecisions() {
        let list = [..._decisions];
        const f = _decisionFilters;
        if (f.search) {
            const q = f.search.toLowerCase();
            list = list.filter((item) => [
                item.code,
                item.text,
                item.rationale,
                item.decided_by,
                item.workshop_name,
                item.workshop_code,
                item.process_step_name,
                item.process_step_code,
            ].join(' ').toLowerCase().includes(q));
        }
        if (f.workshop) list = list.filter((item) => item.workshop_id === f.workshop);
        if (f.status) list = list.filter((item) => item.status === f.status);
        if (f.category) list = list.filter((item) => item.category === f.category);
        if (f.step) list = list.filter((item) => item.process_step_id === f.step);
        return list.sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
    }

    function renderDecisionStatusPill(status) {
        const variant = status === 'active' ? 'success' : status === 'superseded' ? 'draft' : 'danger';
        return ExpUI.pill({ label: (status || 'active').replace(/_/g, ' '), variant, size: 'sm' });
    }

    function renderDecisionWorkspace() {
        const filtered = getFilteredDecisions();
        const active = _decisions.filter((item) => item.status === 'active').length;
        const superseded = _decisions.filter((item) => item.status === 'superseded').length;
        const revoked = _decisions.filter((item) => item.status === 'revoked').length;
        const linkedWorkshops = new Set(_decisions.map((item) => item.workshop_id).filter(Boolean)).size;
        const categories = [...new Set(_decisions.map((item) => item.category).filter(Boolean))].sort();
        const stepsForFilter = (_decisionFilters.workshop && _stepsByWorkshop[_decisionFilters.workshop])
            ? _stepsByWorkshop[_decisionFilters.workshop]
            : Object.values(_stepsById);

        const filterBar = ExpUI.filterBar({
            id: 'outcomesDecisionFilters',
            searchPlaceholder: 'Search decisions...',
            searchValue: _decisionFilters.search,
            onSearch: "ExploreOutcomeHubView.setDecisionFilter('search', this.value)",
            onChange: 'ExploreOutcomeHubView.onDecisionFilterBarChange',
            filters: [
                {
                    id: 'workshop',
                    label: 'Workshop',
                    icon: '📋',
                    type: 'single',
                    color: 'var(--exp-l2)',
                    options: _workshops.map((workshop) => ({
                        value: workshop.id,
                        label: workshop.code ? `${workshop.code} — ${workshop.name || ''}` : (workshop.name || workshop.id),
                    })),
                    selected: _decisionFilters.workshop || '',
                },
                {
                    id: 'status',
                    label: 'Status',
                    icon: '📌',
                    type: 'single',
                    color: 'var(--exp-fit)',
                    options: [
                        { value: 'active', label: 'Active' },
                        { value: 'superseded', label: 'Superseded' },
                        { value: 'revoked', label: 'Revoked' },
                    ],
                    selected: _decisionFilters.status || '',
                },
                {
                    id: 'category',
                    label: 'Category',
                    icon: '🧭',
                    type: 'single',
                    color: 'var(--exp-decision)',
                    options: categories.map((value) => ({ value, label: value.replace(/_/g, ' ') })),
                    selected: _decisionFilters.category || '',
                },
                {
                    id: 'step',
                    label: 'Process Step',
                    icon: '⚙️',
                    type: 'single',
                    color: 'var(--exp-l3)',
                    options: stepsForFilter
                        .map((step) => ({ value: step.id, label: step.code ? `${step.code} — ${step.name || ''}` : (step.name || step.id) }))
                        .sort((a, b) => a.label.localeCompare(b.label)),
                    selected: _decisionFilters.step || '',
                },
            ],
            actionsHtml: `
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                    ${ExpUI.actionButton({ label: '+ Decision', variant: 'primary', size: 'sm', onclick: 'ExploreOutcomeHubView.showDecisionCreateModal()' })}
                    ${ExpUI.actionButton({ label: 'Workshop Hub', variant: 'secondary', size: 'sm', onclick: "App.navigate('explore-workshops')" })}
                </div>
            `,
        });

        const table = !filtered.length
            ? `<div class="exp-empty"><div class="exp-empty__icon">💬</div><div class="exp-empty__title">No decisions captured yet</div><p class="exp-empty__text">Use the decision workspace to capture decisions without leaving Outcomes.</p></div>`
            : `<div class="exp-card">
                <div class="exp-card__body" style="overflow-x:auto">
                    <table class="exp-table">
                        <thead>
                            <tr>
                                <th>Code</th>
                                <th>Decision</th>
                                <th>Workshop</th>
                                <th>Process Step</th>
                                <th>Category</th>
                                <th>Status</th>
                                <th>Decided By</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${filtered.map((item) => {
                                const workshop = getDecisionWorkshop(item);
                                const step = getDecisionStep(item);
                                return `<tr>
                                    <td><code>${esc(item.code || '')}</code></td>
                                    <td>
                                        <div style="font-weight:600">${esc(item.text || item.decision_text || 'Decision')}</div>
                                        <div style="font-size:12px;color:var(--sap-text-secondary);margin-top:4px">${esc(item.rationale || 'No rationale captured.')}</div>
                                    </td>
                                    <td style="font-size:12px">${esc(workshop?.code || item.workshop_code || '')}${(workshop?.name || item.workshop_name) ? `<div style="color:var(--sap-text-secondary);margin-top:4px">${esc(workshop?.name || item.workshop_name)}</div>` : ''}</td>
                                    <td style="font-size:12px">${esc(step.code || item.process_step_code || '')}${(step.name || item.process_step_name) ? `<div style="color:var(--sap-text-secondary);margin-top:4px">${esc(step.name || item.process_step_name)}</div>` : ''}</td>
                                    <td>${item.category ? ExpUI.pill({ label: item.category.replace(/_/g, ' '), variant: 'decision', size: 'sm' }) : '—'}</td>
                                    <td>${renderDecisionStatusPill(item.status)}</td>
                                    <td>${esc(item.decided_by || '—')}</td>
                                    <td>
                                        <div style="display:flex;gap:6px;flex-wrap:wrap">
                                            ${ExpUI.actionButton({ label: 'Edit', variant: 'ghost', size: 'sm', onclick: `ExploreOutcomeHubView.showDecisionEditModal('${item.id}')` })}
                                            ${workshop?.id ? ExpUI.actionButton({ label: 'Workshop', variant: 'ghost', size: 'sm', onclick: `ExploreOutcomeHubView.openWorkshopDetail('${workshop.id}')` }) : ''}
                                            ${ExpUI.actionButton({ label: 'Delete', variant: 'ghost', size: 'sm', onclick: `ExploreOutcomeHubView.deleteDecision('${item.id}')` })}
                                        </div>
                                    </td>
                                </tr>`;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>`;

        return `<div data-testid="explore-outcomes-decisions-workspace">
            <div class="exp-kpi-strip">
                ${ExpUI.kpiBlock({ value: _decisions.length, label: 'Decisions', accent: 'var(--exp-decision)' })}
                ${ExpUI.kpiBlock({ value: active, label: 'Active', accent: 'var(--exp-fit)' })}
                ${ExpUI.kpiBlock({ value: superseded, label: 'Superseded', accent: '#64748b' })}
                ${ExpUI.kpiBlock({ value: revoked, label: 'Revoked', accent: 'var(--exp-gap)' })}
                ${ExpUI.kpiBlock({ value: linkedWorkshops, label: 'Workshops Linked', accent: 'var(--exp-l2)' })}
            </div>
            ${filterBar}
            ${table}
        </div>`;
    }

    function _decisionWorkshopOptions(selectedWorkshopId = '') {
        return _workshops
            .map((workshop) => `<option value="${esc(workshop.id)}" ${selectedWorkshopId === workshop.id ? 'selected' : ''}>${esc(workshop.code ? `${workshop.code} — ${workshop.name || ''}` : (workshop.name || workshop.id))}</option>`)
            .join('');
    }

    function _decisionStepOptions(workshopId, selectedStepId = '') {
        const items = _stepsByWorkshop[workshopId] || [];
        if (!items.length) {
            return '<option value="">No process steps available</option>';
        }
        return [`<option value="">Select process step</option>`]
            .concat(items.map((step) => `<option value="${esc(step.id)}" ${selectedStepId === step.id ? 'selected' : ''}>${esc(step.code ? `${step.code} — ${step.name || ''}` : (step.name || step.id))}</option>`))
            .join('');
    }

    function showDecisionCreateModal() {
        if (!_workshops.length) {
            App.toast('Create a workshop first to capture decisions', 'warning');
            return;
        }
        const defaultWorkshop = _decisionFilters.workshop || _workshops[0]?.id || '';
        const html = `<div class="modal-content outcomes-decision-modal" style="max-width:760px;padding:24px">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:16px">
                <div>
                    <h2 style="margin:0">Create Decision</h2>
                    <p style="margin:6px 0 0;color:var(--sap-text-secondary);font-size:13px">Attach the decision to a workshop process step so it stays traceable inside Outcomes.</p>
                </div>
                <button class="btn btn-secondary btn-sm" onclick="App.closeModal()">Close</button>
            </div>
            <div class="exp-inline-form outcomes-decision-form">
                <div class="exp-inline-form__row exp-inline-form__row--context">
                    <div class="exp-inline-form__field">
                        <label>Workshop</label>
                        <select id="outcomesDecisionWorkshop" onchange="ExploreOutcomeHubView.syncDecisionStepOptions(this.value)">${_decisionWorkshopOptions(defaultWorkshop)}</select>
                    </div>
                    <div class="exp-inline-form__field">
                        <label>Process Step</label>
                        <select id="outcomesDecisionStep" title="Select the process step for this decision">${_decisionStepOptions(defaultWorkshop)}</select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Decision</label><textarea id="outcomesDecisionText" rows="3" placeholder="What was decided?"></textarea></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Decided By</label><input id="outcomesDecisionBy" type="text" placeholder="Name"></div>
                    <div class="exp-inline-form__field">
                        <label>Category</label>
                        <select id="outcomesDecisionCategory">
                            <option value="process">Process</option>
                            <option value="technical">Technical</option>
                            <option value="scope">Scope</option>
                            <option value="organizational">Organizational</option>
                            <option value="data">Data</option>
                        </select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Rationale</label><textarea id="outcomesDecisionRationale" rows="3" placeholder="Why was this decision made?"></textarea></div>
                </div>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Save Decision', variant: 'primary', onclick: 'ExploreOutcomeHubView.submitDecisionCreate()' })}
            </div>
        </div>`;
        App.openModal(html);
    }

    function showDecisionEditModal(decisionId) {
        const decision = _decisions.find((item) => item.id === decisionId);
        if (!decision) {
            App.toast('Decision not found', 'error');
            return;
        }
        const workshop = getDecisionWorkshop(decision);
        const step = getDecisionStep(decision);
        const html = `<div class="modal-content outcomes-decision-modal" style="max-width:760px;padding:24px">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:16px">
                <div>
                    <h2 style="margin:0">Edit Decision</h2>
                    <p style="margin:6px 0 0;color:var(--sap-text-secondary);font-size:13px">${esc(decision.code || 'Decision')} linked to ${esc(workshop?.code || decision.workshop_code || 'Workshop')} / ${esc(step.code || decision.process_step_code || 'Step')}</p>
                </div>
                <button class="btn btn-secondary btn-sm" onclick="App.closeModal()">Close</button>
            </div>
            <div class="exp-inline-form outcomes-decision-form">
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Decision</label><textarea id="outcomesDecisionEditText" rows="3">${esc(decision.text || decision.decision_text || '')}</textarea></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Decided By</label><input id="outcomesDecisionEditBy" type="text" value="${esc(decision.decided_by || '')}"></div>
                    <div class="exp-inline-form__field">
                        <label>Category</label>
                        <select id="outcomesDecisionEditCategory">
                            ${['process', 'technical', 'scope', 'organizational', 'data'].map((value) => `<option value="${value}" ${decision.category === value ? 'selected' : ''}>${value.replace(/_/g, ' ')}</option>`).join('')}
                        </select>
                    </div>
                    <div class="exp-inline-form__field">
                        <label>Status</label>
                        <select id="outcomesDecisionEditStatus">
                            ${['active', 'superseded', 'revoked'].map((value) => `<option value="${value}" ${decision.status === value ? 'selected' : ''}>${value.replace(/_/g, ' ')}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Rationale</label><textarea id="outcomesDecisionEditRationale" rows="4">${esc(decision.rationale || '')}</textarea></div>
                </div>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Save Changes', variant: 'primary', onclick: `ExploreOutcomeHubView.submitDecisionUpdate('${decisionId}')` })}
            </div>
        </div>`;
        App.openModal(html);
    }

    function syncDecisionStepOptions(workshopId, selectedStepId = '') {
        const stepSelect = document.getElementById('outcomesDecisionStep');
        if (!stepSelect) return;
        stepSelect.innerHTML = _decisionStepOptions(workshopId, selectedStepId);
    }

    async function submitDecisionCreate() {
        const workshopId = document.getElementById('outcomesDecisionWorkshop')?.value || '';
        const processStepId = document.getElementById('outcomesDecisionStep')?.value || '';
        const text = (document.getElementById('outcomesDecisionText')?.value || '').trim();
        const decidedBy = (document.getElementById('outcomesDecisionBy')?.value || '').trim();
        const category = document.getElementById('outcomesDecisionCategory')?.value || 'process';
        const rationale = (document.getElementById('outcomesDecisionRationale')?.value || '').trim();

        if (!workshopId || !processStepId) {
            App.toast('Workshop and process step are required', 'error');
            return;
        }
        if (!text || !decidedBy) {
            App.toast('Decision text and decided by are required', 'error');
            return;
        }

        try {
            await ExploreAPI.decisions.create(_pid, workshopId, {
                process_step_id: processStepId,
                text,
                decided_by: decidedBy,
                category,
                rationale: rationale || null,
            });
            App.closeModal();
            App.toast('Decision created', 'success');
            await fetchAll();
            await renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed to create decision', 'error');
        }
    }

    async function submitDecisionUpdate(decisionId) {
        const decision = _decisions.find((item) => item.id === decisionId);
        if (!decision) {
            App.toast('Decision not found', 'error');
            return;
        }

        const text = (document.getElementById('outcomesDecisionEditText')?.value || '').trim();
        const decidedBy = (document.getElementById('outcomesDecisionEditBy')?.value || '').trim();
        const category = document.getElementById('outcomesDecisionEditCategory')?.value || 'process';
        const status = document.getElementById('outcomesDecisionEditStatus')?.value || 'active';
        const rationale = (document.getElementById('outcomesDecisionEditRationale')?.value || '').trim();

        if (!text || !decidedBy) {
            App.toast('Decision text and decided by are required', 'error');
            return;
        }

        try {
            await ExploreAPI.decisions.update(_pid, decision.workshop_id, decisionId, {
                text,
                decided_by: decidedBy,
                category,
                status,
                rationale: rationale || null,
            });
            App.closeModal();
            App.toast('Decision updated', 'success');
            await fetchAll();
            await renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed to update decision', 'error');
        }
    }

    async function deleteDecision(decisionId) {
        const decision = _decisions.find((item) => item.id === decisionId);
        if (!decision) {
            App.toast('Decision not found', 'error');
            return;
        }
        const confirmed = await App.confirmDialog({
            title: 'Delete Decision',
            message: `Delete ${decision.code || 'this decision'}?`,
            confirmLabel: 'Delete',
            testId: 'outcomes-decision-delete-modal',
            confirmTestId: 'outcomes-decision-delete-submit',
            cancelTestId: 'outcomes-decision-delete-cancel',
        });
        if (!confirmed) return;

        try {
            await ExploreAPI.decisions.delete(_pid, decision.workshop_id, decisionId);
            App.toast('Decision deleted', 'success');
            await fetchAll();
            await renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed to delete decision', 'error');
        }
    }

    function setDecisionFilter(key, value) {
        _decisionFilters[key] = value || '';
        void renderPage();
    }

    function onDecisionFilterBarChange(update) {
        if (update._clearAll) {
            _decisionFilters = { search: _decisionFilters.search || '', workshop: '', status: '', category: '', step: '' };
        } else {
            const workshopChanged = Object.prototype.hasOwnProperty.call(update, 'workshop');
            Object.entries(update).forEach(([key, value]) => {
                if (value === null || value === '' || (Array.isArray(value) && value.length === 0)) _decisionFilters[key] = '';
                else _decisionFilters[key] = Array.isArray(value) ? value[0] : value;
            });
            if (workshopChanged) {
                _decisionFilters.step = '';
            }
        }
        void renderPage();
    }

    function openWorkshopDetail(workshopId) {
        if (!workshopId) {
            App.toast('Workshop not found', 'warning');
            return;
        }
        localStorage.setItem('exp_selected_workshop', workshopId);
        App.navigate('explore-workshop-detail');
    }

    function renderWorkspaceBody() {
        if (_workspace === 'stream') {
            return `<div data-testid="explore-outcomes-stream">
                ${renderFilterBar()}
                ${renderStreamList()}
            </div>`;
        }
        if (_workspace === 'decisions') {
            return renderDecisionWorkspace();
        }

        return `<div id="outcomesWorkspaceContent">
            <div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:240px">
                <div style="text-align:center;color:var(--sap-text-secondary)">
                    <div style="font-size:28px;margin-bottom:8px">⏳</div>
                    Loading workspace…
                </div>
            </div>
        </div>`;
    }

    async function renderEmbeddedWorkspace() {
        if (_workspace === 'requirements') {
            await ExploreRequirementHubView.renderEmbedded({
                containerId: 'outcomesWorkspaceContent',
                tab: 'requirements',
                hideTabs: true,
            });
            return;
        }
        if (_workspace === 'openItems') {
            await ExploreRequirementHubView.renderEmbedded({
                containerId: 'outcomesWorkspaceContent',
                tab: 'openItems',
                hideTabs: true,
            });
            return;
        }
        if (_workspace === 'handoff') {
            await ExploreTraceabilityHubView.renderEmbedded({
                containerId: 'outcomesWorkspaceContent',
                title: _pageTitle === 'Handoff & Traceability' ? 'Handoff Workspace' : 'Handoff & Traceability',
            });
        }
    }

    async function renderPage() {
        const main = document.getElementById('mainContent');
        main.innerHTML = `<div class="explore-page" data-testid="${_pageTestId}">
            ${PGBreadcrumb.html([{ label: 'Programs', onclick: 'App.navigate("programs")' }, { label: 'Explore' }, { label: _breadcrumbLabel }])}
            ${renderHeader()}
            ${renderStageNav()}
            ${renderLoadWarnings()}
            ${renderWorkspaceTabs()}
            ${renderWorkspaceBody()}
        </div>`;

        if (_workspace !== 'stream') {
            await renderEmbeddedWorkspace();
        }
    }

    function renderLoading(label = 'Loading outcomes…') {
        const main = document.getElementById('mainContent');
        main.innerHTML = `<div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:300px">
            <div style="text-align:center;color:var(--sap-text-secondary)"><div style="font-size:28px;margin-bottom:8px">⏳</div>${esc(label)}</div>
        </div>`;
    }

    function renderError(message) {
        const main = document.getElementById('mainContent');
        main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error</div><p class="exp-empty__text">${esc(message || 'Unknown error')}</p></div>`;
    }

    function navigateToWorkspace(workspace, streamTab = '') {
        _persistWorkspaceState({ workspace, streamTab });
        App.navigate('explore-outcomes');
    }

    function openCreateRequirement() {
        _persistWorkspaceState({ workspace: 'requirements', openCreate: 'requirement' });
        App.navigate('explore-outcomes');
    }

    function openCreateOpenItem() {
        _persistWorkspaceState({ workspace: 'openItems', openCreate: 'openItem' });
        App.navigate('explore-outcomes');
    }

    function openCreateDecision() {
        _persistWorkspaceState({ workspace: 'decisions', openCreate: 'decision' });
        App.navigate('explore-outcomes');
    }

    function setFilter(key, value) {
        _filters[key] = value || '';
        void renderPage();
    }

    function onFilterBarChange(update) {
        if (update._clearAll) {
            _filters = { search: _filters.search || '', workshop: '', status: '', owner: '' };
        } else {
            Object.entries(update).forEach(([key, value]) => {
                if (value === null || value === '' || (Array.isArray(value) && value.length === 0)) _filters[key] = '';
                else _filters[key] = Array.isArray(value) ? value[0] : value;
            });
        }
        void renderPage();
    }

    async function render(options = {}) {
        const main = document.getElementById('mainContent');
        const project = App.getActiveProject();
        if (!project) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">📋</div><div class="exp-empty__title">Select a project first</div></div>`;
            return;
        }

        _pid = project.id;
        const pending = _consumeWorkspaceState();
        const workspace = pending?.workspace || options.workspace || 'stream';
        const streamTab = pending?.streamTab || options.streamTab || '';
        const openCreate = pending?.openCreate || options.openCreate || '';
        _pageTitle = options.pageTitle || 'Explore Outcomes';
        _pageSubtitle = options.pageSubtitle || 'Single cockpit to manage workshop outputs, readiness, and downstream handoff.';
        _breadcrumbLabel = options.breadcrumbLabel || 'Outcomes';
        _pageTestId = options.pageTestId || 'explore-outcomes-page';
        _selectWorkspace(workspace, streamTab);

        renderLoading(
            _workspace === 'handoff'
                ? 'Loading handoff workspace…'
                : _workspace === 'requirements'
                    ? 'Loading requirements workspace…'
                    : _workspace === 'decisions'
                        ? 'Loading decisions workspace…'
                    : _workspace === 'openItems'
                        ? 'Loading open item workspace…'
                        : 'Loading outcomes…'
        );

        try {
            await fetchAll();
            await renderPage();
            if (openCreate === 'decision') {
                setTimeout(() => { showDecisionCreateModal(); }, 0);
            } else if (openCreate === 'requirement') {
                setTimeout(() => { ExploreRequirementHubView.createRequirement(); }, 0);
            } else if (openCreate === 'openItem') {
                setTimeout(() => { ExploreRequirementHubView.createOpenItem(); }, 0);
            }
        } catch (err) {
            renderError(err.message);
        }
    }

    function renderForRequirementRoute() {
        return render({
            workspace: _resolveRequirementRouteWorkspace(),
            pageTitle: 'Requirements & Open Items',
            pageSubtitle: 'Track, manage, and govern all explore-phase requirements and open items.',
            breadcrumbLabel: 'Requirements & Open Items',
            pageTestId: 'explore-requirements-page',
        });
    }

    function renderForTraceabilityRoute() {
        return render({
            workspace: 'handoff',
            pageTitle: 'Handoff & Traceability',
            pageSubtitle: 'Verify requirement lineage and move approved outcomes into backlog and downstream delivery.',
            breadcrumbLabel: 'Handoff & Traceability',
            pageTestId: 'explore-traceability-page',
        });
    }

    return {
        render,
        renderForRequirementRoute,
        renderForTraceabilityRoute,
        navigateToWorkspace,
        openCreateDecision,
        openCreateRequirement,
        openCreateOpenItem,
        showDecisionCreateModal,
        showDecisionEditModal,
        syncDecisionStepOptions,
        submitDecisionCreate,
        submitDecisionUpdate,
        deleteDecision,
        setDecisionFilter,
        onDecisionFilterBarChange,
        openWorkshopDetail,
        setFilter,
        onFilterBarChange,
    };
})();

const ExploreTraceabilityHubView = (() => {
    'use strict';

    const esc = ExpUI.esc;
    const NAV_STATE_KEY = 'pg.exploreRequirementsNavState';
    const OUTCOMES_WORKSPACE_KEY = 'pg.exploreOutcomesWorkspace';

    let _pid = null;
    let _requirements = [];
    let _openItems = [];
    let _renderMode = 'page';
    let _renderContainerId = null;
    let _embeddedTitle = 'Handoff & Traceability';

    function _ensureProgramContext() {
        if (_pid) return _pid;
        const project = App.getActiveProject();
        _pid = project?.id || null;
        return _pid;
    }

    function _resolveRenderHost() {
        if (_renderMode === 'embedded' && _renderContainerId) {
            return document.getElementById(_renderContainerId);
        }
        return document.getElementById('mainContent');
    }

    function _renderHostHtml(html) {
        const host = _resolveRenderHost();
        if (host) host.innerHTML = html;
    }

    function _renderLoading(label = 'Loading traceability…') {
        _renderHostHtml(`<div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:300px">
            <div style="text-align:center;color:var(--sap-text-secondary)"><div style="font-size:28px;margin-bottom:8px">⏳</div>${esc(label)}</div>
        </div>`);
    }

    function _renderError(message) {
        _renderHostHtml(`<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error</div><p class="exp-empty__text">${esc(message || 'Unknown error')}</p></div>`);
    }

    function _navigateToRequirementHub(state = null) {
        try {
            if (state) {
                sessionStorage.setItem(NAV_STATE_KEY, JSON.stringify(state));
                sessionStorage.setItem(OUTCOMES_WORKSPACE_KEY, JSON.stringify({
                    workspace: state.tab === 'openItems' ? 'openItems' : 'requirements',
                }));
            } else {
                sessionStorage.removeItem(NAV_STATE_KEY);
                sessionStorage.removeItem(OUTCOMES_WORKSPACE_KEY);
            }
        } catch {
            // Ignore storage failures; navigation still works.
        }
        App.navigate('explore-outcomes');
    }

    function openBatchConvertReady() {
        _navigateToRequirementHub({
            tab: 'requirements',
            postAction: 'batchConvertReady',
        });
    }

    function openOpenItemQueue() {
        _navigateToRequirementHub({
            tab: 'openItems',
            oiFilters: {
                queueOnly: true,
            },
        });
    }

    async function fetchAll() {
        const [requirements, openItems] = await Promise.all([
            ExploreAPI.requirements.list(_pid),
            ExploreAPI.openItems.list(_pid),
        ]);
        _requirements = requirements || [];
        _openItems = openItems || [];
    }

    function traceMetrics() {
        return {
            total: _requirements.length,
            linked: _requirements.filter((item) => item.backlog_item_id || item.config_item_id).length,
            ready: _requirements.filter((item) => item.status === 'approved' && !item.backlog_item_id && !item.config_item_id).length,
            blocked: _requirements.filter((item) => (item.linked_open_items || []).length > 0).length,
            missingSource: _requirements.filter((item) => !item.workshop_code && !item.scope_item_code && !item.l4_code).length,
            unresolvedItems: _openItems.filter((item) => !['closed', 'resolved'].includes(item.status)).length,
        };
    }

    function renderEmbeddedIntro(title = 'Handoff & Traceability') {
        return `<div class="exp-card" style="margin-bottom:var(--exp-space-lg)">
            <div class="exp-card__body" style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap">
                <div>
                    <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--sap-text-secondary);font-weight:700">Outcomes Workspace</div>
                    <h2 style="margin:6px 0 4px;font-size:28px">${esc(title)}</h2>
                    <p style="margin:0;color:var(--sap-text-secondary)">Validate lineage, clear blockers, and move approved requirements into backlog-ready delivery scope.</p>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap">
                    ${ExpUI.actionButton({ label: 'Outcome Stream', variant: 'secondary', size: 'sm', onclick: "ExploreOutcomeHubView.navigateToWorkspace('stream')" })}
                    ${ExpUI.actionButton({ label: 'Requirement Workspace', variant: 'ghost', size: 'sm', onclick: "ExploreOutcomeHubView.navigateToWorkspace('requirements')" })}
                </div>
            </div>
        </div>`;
    }

    function renderPage() {
        const metrics = traceMetrics();
        const handoffRows = _requirements
            .slice()
            .sort((a, b) => (a.backlog_item_id || a.config_item_id ? 1 : 0) - (b.backlog_item_id || b.config_item_id ? 1 : 0))
            .map((item) => {
                const linked = item.backlog_item_id || item.config_item_id;
                const blockers = (item.linked_open_items || []).length;
                return `<tr>
                    <td><code>${esc(item.code || item.id || 'REQ')}</code></td>
                    <td>${esc(item.title || 'Untitled requirement')}</td>
                    <td>${esc(item.workshop_code || item.workshop_name || '—')}</td>
                    <td>${esc(item.scope_item_code || item.scope_item_name || item.l4_code || '—')}</td>
                    <td>${linked ? (item.backlog_item_id ? `WRICEF #${item.backlog_item_id}` : `CFG #${item.config_item_id}`) : 'Pending handoff'}</td>
                    <td>${blockers ? `${blockers} blocker(s)` : 'Clear'}</td>
                    <td>${esc(item.cloud_alm_id || item.alm_id || '—')}</td>
                </tr>`;
            }).join('');

        _renderHostHtml(`<div class="explore-page" data-testid="${_renderMode === 'embedded' ? 'explore-traceability-embedded' : 'explore-traceability-page'}">
            ${_renderMode === 'page'
                ? `${PGBreadcrumb.html([{ label: 'Programs', onclick: 'App.navigate("programs")' }, { label: 'Explore' }, { label: 'Handoff & Traceability' }])}
                    <div class="explore-page__header">
                        <div>
                            <h1 class="explore-page__title">Handoff & Traceability</h1>
                            <p class="explore-page__subtitle">Verify requirement lineage and move approved outcomes into backlog and downstream delivery.</p>
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap">
                            ${ExpUI.actionButton({ label: 'Outcome Stream', variant: 'secondary', onclick: "App.navigate('explore-outcomes')" })}
                            ${ExpUI.actionButton({ label: 'Open Requirement Hub', variant: 'ghost', onclick: "ExploreOutcomeHubView.navigateToWorkspace('requirements')" })}
                        </div>
                    </div>
                    ${ExpUI.exploreStageNav({ current: 'explore-traceability' })}`
                : renderEmbeddedIntro(_embeddedTitle)}

            <div class="exp-kpi-strip">
                ${ExpUI.kpiBlock({ value: metrics.total, label: 'Requirements', accent: 'var(--exp-requirement)' })}
                ${ExpUI.kpiBlock({ value: metrics.linked, label: 'Linked to Backlog', accent: 'var(--exp-fit)' })}
                ${ExpUI.kpiBlock({ value: metrics.ready, label: 'Ready to Convert', accent: '#3b82f6' })}
                ${ExpUI.kpiBlock({ value: metrics.blocked, label: 'Blocked by OIs', accent: 'var(--exp-open-item)' })}
                ${ExpUI.kpiBlock({ value: metrics.missingSource, label: 'Missing Source Trace', accent: 'var(--exp-gap)' })}
                ${ExpUI.kpiBlock({ value: metrics.unresolvedItems, label: 'Open Item Queue', accent: '#64748b' })}
            </div>

            <div style="display:grid;grid-template-columns:1.1fr .9fr;gap:var(--exp-space-lg);margin-bottom:var(--exp-space-lg)">
                <div class="exp-card">
                    <div class="exp-card__header">Handoff Priorities</div>
                    <div class="exp-card__body" style="display:grid;gap:10px">
                        <div class="exp-detail-row"><span class="exp-detail-row__label">Approved but not converted</span><span class="exp-detail-row__value">${metrics.ready}</span></div>
                        <div class="exp-detail-row"><span class="exp-detail-row__label">Requirements with blockers</span><span class="exp-detail-row__value">${metrics.blocked}</span></div>
                        <div class="exp-detail-row"><span class="exp-detail-row__label">Requirements missing workshop/scope link</span><span class="exp-detail-row__value">${metrics.missingSource}</span></div>
                        <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
                            ${ExpUI.actionButton({ label: 'Batch Convert Ready', variant: 'primary', size: 'sm', onclick: 'ExploreTraceabilityHubView.openBatchConvertReady()' })}
                            ${ExpUI.actionButton({ label: 'Open Item Queue', variant: 'secondary', size: 'sm', onclick: 'ExploreTraceabilityHubView.openOpenItemQueue()' })}
                        </div>
                    </div>
                </div>
                <div class="exp-card">
                    <div class="exp-card__header">Trace Rules</div>
                    <div class="exp-card__body" style="font-size:13px;color:var(--sap-text-secondary);display:grid;gap:8px">
                        <div>Every requirement should point back to a workshop or scoped process step.</div>
                        <div>Approved requirements should either convert to a WRICEF/config item or be explicitly deferred.</div>
                        <div>Linked open items should be cleared before final backlog handoff and test planning.</div>
                    </div>
                </div>
            </div>

            <div class="exp-card explore-trace-table">
                <div class="exp-card__header">Requirement Trace Matrix</div>
                <div class="exp-card__body" style="overflow-x:auto">
                    <table class="exp-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Requirement</th>
                                <th>Workshop</th>
                                <th>Scope</th>
                                <th>Backlog / Config</th>
                                <th>Blockers</th>
                                <th>ALM</th>
                            </tr>
                        </thead>
                        <tbody>${handoffRows || '<tr><td colspan="7" style="text-align:center;color:var(--sap-text-secondary)">No requirements available</td></tr>'}</tbody>
                    </table>
                </div>
            </div>
        </div>`);
    }

    async function _renderView({ mode = 'page', containerId = null } = {}) {
        _renderMode = mode;
        _renderContainerId = mode === 'embedded' ? containerId : null;

        if (!_ensureProgramContext()) {
            _renderHostHtml(`<div class="exp-empty"><div class="exp-empty__icon">📋</div><div class="exp-empty__title">Select a project first</div></div>`);
            return;
        }

        _renderLoading(_renderMode === 'embedded' ? 'Loading handoff workspace…' : 'Loading traceability…');
        try {
            await fetchAll();
            renderPage();
        } catch (err) {
            _renderError(err.message);
        }
    }

    async function render() {
        return _renderView();
    }

    async function renderEmbedded({ containerId, title = 'Handoff & Traceability' } = {}) {
        _embeddedTitle = title;
        return _renderView({ mode: 'embedded', containerId });
    }

    return { render, renderEmbedded, openBatchConvertReady, openOpenItemQueue };
})();
