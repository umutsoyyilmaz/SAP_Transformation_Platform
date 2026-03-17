const TestOverviewView = (() => {
    const esc = TestingShared.esc;

    let _pid = null;
    let _summary = {};
    let _approvals = [];
    let _cycleRisk = [];
    let _cycleRiskSummary = {};
    let _retestReadiness = [];
    let _retestSummary = {};
    let _releaseReadiness = [];
    let _releaseReadinessSummary = {};

    async function fetchAll() {
        const payload = await API.get(`/programs/${_pid}/testing/overview-summary`);
        _summary = payload?.summary || {};
        _approvals = payload?.approvals || [];
        _cycleRisk = payload?.cycle_risk || [];
        _cycleRiskSummary = payload?.cycle_risk_summary || {};
        _retestReadiness = payload?.retest_readiness || [];
        _retestSummary = payload?.retest_summary || {};
        _releaseReadiness = payload?.release_readiness || [];
        _releaseReadinessSummary = payload?.release_readiness_summary || {};
    }

    function aggregate() {
        return {
            totalCases: 0,
            readyCases: 0,
            draftCases: 0,
            plans: 0,
            cycles: 0,
            executions: 0,
            fail: 0,
            blocked: 0,
            pass: 0,
            pending: 0,
            openDefects: 0,
            criticalDefects: 0,
            retestQueue: 0,
            pendingApprovals: 0,
            highRiskCycles: _cycleRiskSummary.high_risk_cycles || _cycleRisk.filter((item) => item.risk === 'high').length,
            readyRetests: _retestSummary.ready_now || _retestReadiness.filter((item) => item.readiness === 'ready_now').length,
            approvalBlockedRetests: _retestSummary.awaiting_approval || _retestReadiness.filter((item) => item.readiness === 'awaiting_approval').length,
            needsLinkedRetests: _retestSummary.needs_linkage || _retestReadiness.filter((item) => item.readiness === 'needs_linkage').length,
            releaseReadyCycles: _releaseReadinessSummary.ready_now || _releaseReadiness.filter((item) => item.readiness === 'ready_now').length,
            releaseBlockedCycles: Math.max(0, (_releaseReadinessSummary.total_cycles || _releaseReadiness.length) - (_releaseReadinessSummary.ready_now || 0)),
            ...(_summary || {}),
        };
    }

    function renderKpis(summary) {
        return `<div class="exp-kpi-strip">
            ${ExpUI.kpiBlock({ value: summary.executions, label: 'Executions in Flight', accent: '#0070f2' })}
            ${ExpUI.kpiBlock({ value: summary.fail, label: 'Failed', accent: '#dc2626' })}
            ${ExpUI.kpiBlock({ value: summary.blocked, label: 'Blocked', accent: '#f59e0b' })}
            ${ExpUI.kpiBlock({ value: summary.openDefects, label: 'Open Defects', accent: '#991b1b' })}
            ${ExpUI.kpiBlock({ value: summary.highRiskCycles, label: 'High-Risk Cycles', accent: '#9f1239' })}
            ${ExpUI.kpiBlock({ value: summary.retestQueue, label: 'Retest Queue', accent: '#7c3aed' })}
            ${ExpUI.kpiBlock({ value: summary.pendingApprovals, label: 'Pending Approvals', accent: '#0f766e' })}
            ${ExpUI.kpiBlock({ value: summary.releaseReadyCycles, label: 'Release-Ready Cycles', accent: '#107e3e' })}
        </div>`;
    }

    function renderFocusGrid(summary) {
        const cards = [
            {
                title: 'Execution Center',
                copy: 'Run today’s cycles, focus blocked and failed executions, and drive retest decisions.',
                metric: `${summary.executions} execution records`,
                route: 'execution-center',
            },
            {
                title: 'Plans & Cases',
                copy: 'Shape suites, plans, and test catalog coverage before execution starts.',
                metric: `${summary.totalCases} cases / ${summary.plans} plans`,
                route: 'test-planning',
            },
            {
                title: 'Defects & Retest',
                copy: 'Triage failures, monitor SLA risk, and keep the retest queue visible.',
                metric: `${summary.openDefects} open / ${summary.criticalDefects} critical`,
                route: 'defects-retest',
            },
            {
                title: 'Approvals & Sign-off',
                copy: 'Review pending approvals and the final sign-off readiness chain.',
                metric: `${summary.pendingApprovals} pending approvals`,
                route: 'signoff-approvals',
            },
        ];
        return `<div class="explore-spotlight-grid">
            ${cards.map((card) => `
                <button class="explore-spotlight-card" type="button" onclick="App.navigate('${card.route}')">
                    <span class="explore-spotlight-card__eyebrow">Work Area</span>
                    <span class="explore-spotlight-card__title">${esc(card.title)}</span>
                    <span class="explore-spotlight-card__copy">${esc(card.copy)}</span>
                    <span class="explore-spotlight-card__metric">${esc(card.metric)}</span>
                </button>
            `).join('')}
        </div>`;
    }

    function renderActionPanels(summary) {
        const queue = [
            { label: 'Failures awaiting triage', value: summary.fail, route: 'defects-retest' },
            { label: 'Retest queue', value: summary.retestQueue, route: 'defects-retest' },
            { label: 'Pending approvals', value: summary.pendingApprovals, route: 'signoff-approvals' },
            { label: 'Draft test cases', value: summary.draftCases, route: 'test-planning' },
        ];
        const readiness = [
            { label: 'Ready test cases', value: summary.readyCases },
            { label: 'Planned cycles', value: summary.cycles },
            { label: 'Passed executions', value: summary.pass },
            { label: 'Pending executions', value: summary.pending },
        ];

        return `<div style="display:grid;grid-template-columns:1.1fr .9fr;gap:var(--exp-space-lg);margin-top:var(--exp-space-lg)">
            <div class="exp-card">
                <div class="exp-card__header">Operational Queue</div>
                <div class="exp-card__body" style="display:grid;gap:10px">
                    ${queue.map((item) => `
                        <button type="button" class="explore-spotlight-card" style="padding:14px" onclick="App.navigate('${item.route}')">
                            <span class="explore-spotlight-card__title" style="font-size:14px">${esc(item.label)}</span>
                            <span class="explore-spotlight-card__metric">${item.value}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
            <div class="exp-card">
                <div class="exp-card__header">Readiness Snapshot</div>
                <div class="exp-card__body" style="display:grid;gap:10px">
                    ${readiness.map((item) => `
                        <div class="exp-detail-row">
                            <span class="exp-detail-row__label">${esc(item.label)}</span>
                            <span class="exp-detail-row__value">${item.value}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>`;
    }

    function renderReleaseReadinessChain(summary) {
        if (!_releaseReadiness.length) return '';
        const rows = _releaseReadiness.slice(0, 5);
        return `<div class="exp-card" data-testid="release-readiness-panel" style="margin-top:var(--exp-space-lg)">
            <div class="exp-card__header">Release Readiness Chain</div>
            <div class="exp-card__body" style="display:grid;gap:10px">
                <div class="exp-detail-row">
                    <span class="exp-detail-row__label">Ready cycles / Blocked cycles / Go-No-Go</span>
                    <span class="exp-detail-row__value">${summary.releaseReadyCycles} / ${summary.releaseBlockedCycles} / ${esc(String(_releaseReadinessSummary.go_no_go_overall || 'n/a').toUpperCase())}</span>
                </div>
                ${rows.map((row) => `
                    <div class="exp-detail-row">
                        <div>
                            <div style="font-weight:600">${esc(row.cycle_name || 'Cycle')}</div>
                            <div class="tm-muted">${esc(row.environment || '—')} · ${esc(row.build_tag || '—')} · ${esc(row.transport_request || '—')} · ${esc(row.owner || '—')}</div>
                            <div class="tm-muted">${esc(row.next_action || '')}</div>
                        </div>
                        <span style="font-weight:700;color:${row.readiness === 'ready_now' ? '#107e3e' : '#b45309'}">${esc(row.readiness || 'unknown')}</span>
                    </div>
                `).join('')}
            </div>
        </div>`;
    }

    function riskTone(risk) {
        if (risk === 'high') return '#b91c1c';
        if (risk === 'medium') return '#b45309';
        return '#166534';
    }

    function readinessTone(readiness) {
        if (readiness === 'ready_now') return '#166534';
        if (readiness === 'awaiting_approval' || readiness === 'case_only') return '#b45309';
        return '#b91c1c';
    }

    function renderEmptyLine(message) {
        return `<div class="exp-detail-row"><span class="exp-detail-row__label">${esc(message)}</span></div>`;
    }

    function renderManagerRiskBoard(summary) {
        const rows = [..._cycleRisk].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).slice(0, 5);
        return `<div class="exp-card" data-testid="manager-risk-board">
            <div class="exp-card__header">Cycle Sign-off Risk</div>
            <div class="exp-card__body" style="display:grid;gap:10px">
                <div class="exp-detail-row">
                    <span class="exp-detail-row__label">High-risk cycles</span>
                    <span class="exp-detail-row__value">${summary.highRiskCycles}</span>
                </div>
                ${rows.length ? rows.map((row) => `
                    <div class="exp-detail-row">
                        <div>
                            <div style="font-weight:600">${esc(row.cycle_name || 'Cycle')}</div>
                            <div class="tm-muted">${esc(row.plan_name || 'Unplanned')} · Fail ${row.failed || 0} · Blocked ${row.blocked || 0}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:10px">
                            <span style="font-weight:700;color:${riskTone(row.risk)}">${esc(row.risk || 'low')}</span>
                            <button class="tm-toolbar__btn tm-toolbar__btn--primary" onclick="App.navigate('execution-center')">Open</button>
                        </div>
                    </div>
                `).join('') : renderEmptyLine('No cycle risk rows available yet.')}
            </div>
        </div>`;
    }

    function renderLeadOpsBoard(summary) {
        const rows = [..._retestReadiness].slice(0, 5);
        return `<div class="exp-card" data-testid="lead-ops-board">
            <div class="exp-card__header">Retest Operations Desk</div>
            <div class="exp-card__body" style="display:grid;gap:10px">
                <div class="exp-detail-row">
                    <span class="exp-detail-row__label">Ready now / Awaiting approval / Needs linkage</span>
                    <span class="exp-detail-row__value">${summary.readyRetests} / ${summary.approvalBlockedRetests} / ${summary.needsLinkedRetests}</span>
                </div>
                ${rows.length ? rows.map((row) => `
                    <div class="exp-detail-row">
                        <div>
                            <div style="font-weight:600">${esc(row.title || row.defect_code || 'Defect')}</div>
                            <div class="tm-muted">${esc(row.plan_name || 'No plan')} · ${esc(row.cycle_name || 'No cycle')} · ${esc(row.next_action || 'Review retest path')}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:10px">
                            <span style="font-weight:700;color:${readinessTone(row.readiness)}">${esc(row.readiness || 'unknown')}</span>
                            <button class="tm-toolbar__btn tm-toolbar__btn--primary" onclick="App.navigate('defects-retest')">Open</button>
                        </div>
                    </div>
                `).join('') : renderEmptyLine('No retest items waiting for lead action.')}
            </div>
        </div>`;
    }

    function renderBusinessApprovalBoard(summary) {
        const approvalRows = [..._approvals].slice(0, 5);
        const cycleRows = [..._cycleRisk]
            .filter((row) => (row.pending_approvals || 0) > 0 || (row.pending_signoffs || 0) > 0)
            .slice(0, 4);

        return `<div class="exp-card" data-testid="business-approval-board">
            <div class="exp-card__header">Business Sign-off Board</div>
            <div class="exp-card__body" style="display:grid;gap:10px">
                <div class="exp-detail-row">
                    <span class="exp-detail-row__label">Pending approvals / approval-blocked retests</span>
                    <span class="exp-detail-row__value">${summary.pendingApprovals} / ${summary.approvalBlockedRetests}</span>
                </div>
                ${approvalRows.length ? approvalRows.map((row) => `
                    <div class="exp-detail-row">
                        <div>
                            <div style="font-weight:600">${esc(row.name || row.title || `${row.entity_type} #${row.entity_id}`)}</div>
                            <div class="tm-muted">${esc(row.entity_type || 'approval')} · approver ${esc(row.approver || row.role || 'pending')}</div>
                        </div>
                        <button class="tm-toolbar__btn tm-toolbar__btn--primary" onclick="App.navigate('signoff-approvals')">Review</button>
                    </div>
                `).join('') : renderEmptyLine('No business approvals are pending right now.')}
                ${cycleRows.length ? `
                    <div style="margin-top:4px;padding-top:10px;border-top:1px solid var(--exp-border)">
                        ${cycleRows.map((row) => `
                            <div class="exp-detail-row">
                                <span class="exp-detail-row__label">${esc(row.cycle_name || 'Cycle')} · Sign-offs ${row.pending_signoffs || 0}</span>
                                <span class="exp-detail-row__value">${row.readiness || 0}%</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        </div>`;
    }

    function renderRoleOperationalBoard(workspace, summary) {
        if (workspace === 'lead') return renderLeadOpsBoard(summary);
        if (workspace === 'business') return renderBusinessApprovalBoard(summary);
        return renderManagerRiskBoard(summary);
    }

    function renderWorkspaceOpsRail(workspace, summary) {
        const tilesByMode = {
            manager: [
                { label: 'High-risk cycles', value: summary.highRiskCycles, route: 'execution-center' },
                { label: 'Pending approvals', value: summary.pendingApprovals, route: 'signoff-approvals' },
                { label: 'Ready retests', value: summary.readyRetests, route: 'defects-retest' },
            ],
            lead: [
                { label: 'Blocked executions', value: summary.blocked, route: 'execution-center' },
                { label: 'Retests ready now', value: summary.readyRetests, route: 'defects-retest' },
                { label: 'Needs linkage', value: summary.needsLinkedRetests, route: 'defects-retest' },
            ],
            business: [
                { label: 'Pending sign-off actions', value: summary.pendingApprovals, route: 'signoff-approvals' },
                { label: 'Awaiting approval retests', value: summary.approvalBlockedRetests, route: 'defects-retest' },
                { label: 'Ready executions', value: summary.pending, route: 'execution-center' },
            ],
        };
        const tiles = tilesByMode[workspace] || tilesByMode.manager;
        return `<div class="exp-card" data-testid="role-workspace-actions">
            <div class="exp-card__header">Operational Actions</div>
            <div class="exp-card__body" style="display:grid;gap:10px">
                ${tiles.map((item) => `
                    <button type="button" class="explore-spotlight-card" style="padding:14px" onclick="App.navigate('${item.route}')">
                        <span class="explore-spotlight-card__title" style="font-size:14px">${esc(item.label)}</span>
                        <span class="explore-spotlight-card__metric">${item.value}</span>
                    </button>
                `).join('')}
            </div>
        </div>`;
    }

    function renderRoleCockpit(summary) {
        const ctx = TestingShared.getRoleContext();
        const cardsByMode = {
            manager: [
                { label: 'Execution capacity', value: summary.executions, note: 'Live execution volume across visible cycles', route: 'execution-center' },
                { label: 'Critical defects', value: summary.criticalDefects, note: 'Immediate sign-off blockers', route: 'defects-retest' },
                { label: 'Pending approvals', value: summary.pendingApprovals, note: 'Completion chain waiting for sign-off', route: 'signoff-approvals' },
            ],
            lead: [
                { label: 'Blocked tests', value: summary.blocked, note: 'Unblock before the next execution wave', route: 'execution-center' },
                { label: 'Retest queue', value: summary.retestQueue, note: 'Fixed defects waiting for confirmation', route: 'defects-retest' },
                { label: 'Approval pressure', value: summary.pendingApprovals, note: 'Lead action needed to close cycles', route: 'signoff-approvals' },
            ],
            business: [
                { label: 'Ready to run', value: summary.pending, note: 'Scenarios still waiting for execution', route: 'execution-center' },
                { label: 'Need evidence', value: summary.fail + summary.blocked, note: 'Failed or blocked steps to document clearly', route: 'execution-center' },
                { label: 'Awaiting sign-off', value: summary.pendingApprovals, note: 'Business confirmation still outstanding', route: 'signoff-approvals' },
            ],
        };
        const cards = cardsByMode[ctx.mode] || cardsByMode.manager;

        return `<div class="exp-card" data-testid="role-cockpit-panel" style="margin-top:var(--exp-space-lg)">
            <div class="exp-card__header">Role-Based Cockpit</div>
            <div class="exp-card__body" style="display:grid;gap:12px">
                <div>
                    <div class="explore-spotlight-card__eyebrow">Workspace Mode</div>
                    <h2 style="margin:4px 0 6px">${esc(ctx.title)}</h2>
                    <p style="margin:0;color:var(--exp-text-muted)">${esc(ctx.subtitle)}</p>
                </div>
                <div style="display:flex;justify-content:flex-end">
                    ${ExpUI.actionButton({ label: 'Open Workspace', variant: 'primary', size: 'sm', onclick: `App.navigate('${ctx.route}')` })}
                </div>
                <div class="explore-spotlight-grid" data-testid="role-cockpit-grid">
                    ${cards.map((card) => `
                        <button class="explore-spotlight-card" type="button" onclick="App.navigate('${card.route}')">
                            <span class="explore-spotlight-card__title">${esc(card.label)}</span>
                            <span class="explore-spotlight-card__metric">${card.value}</span>
                            <span class="explore-spotlight-card__copy">${esc(card.note)}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
        </div>`;
    }

    function renderWorkspace(modeOverride, summary) {
        const ctx = TestingShared.getRoleContext();
        const workspace = modeOverride || ctx.mode;
        const headingMap = {
            manager: 'Test Manager Cockpit',
            lead: 'SIT / UAT Lead Cockpit',
            business: 'Business Tester Workspace',
        };
        const subtitleMap = {
            manager: 'Capacity, blocker, and approval control room for the active testing portfolio.',
            lead: 'Operational lead workspace for unblock, retest, and sign-off coordination.',
            business: 'Execution-first workspace focused on evidence, blocked steps, and business confirmation.',
        };
        const cardsByMode = {
            manager: [
                { title: 'Portfolio Readiness', copy: `${summary.plans} plans and ${summary.cycles} cycles in active scope.`, metric: `${summary.pendingApprovals} approvals pending`, route: 'signoff-approvals' },
                { title: 'Execution Risk', copy: `${summary.fail} failed and ${summary.blocked} blocked executions need action.`, metric: `${summary.criticalDefects} critical defects`, route: 'execution-center' },
                { title: 'Retest Pressure', copy: 'Watch fix verification before sign-off windows close.', metric: `${summary.retestQueue} defects in retest queue`, route: 'defects-retest' },
            ],
            lead: [
                { title: 'Blocker Desk', copy: 'Own the unblock flow before the next cycle window opens.', metric: `${summary.blocked} blocked executions`, route: 'execution-center' },
                { title: 'Retest Coordination', copy: 'Move fixed defects back into executable scenarios.', metric: `${summary.retestQueue} waiting for retest`, route: 'defects-retest' },
                { title: 'Approval Watch', copy: 'Lead action needed to close UAT and final sign-off gaps.', metric: `${summary.pendingApprovals} pending approvals`, route: 'signoff-approvals' },
            ],
            business: [
                { title: 'Run Today', copy: 'Open ready scenarios and capture evidence directly from execution.', metric: `${summary.pending} pending executions`, route: 'execution-center' },
                { title: 'Evidence Gaps', copy: 'Failed and blocked scenarios still need clear business evidence.', metric: `${summary.fail + summary.blocked} need documentation`, route: 'execution-center' },
                { title: 'Sign-off Actions', copy: 'Complete business confirmations without navigating planning-heavy screens.', metric: `${summary.pendingApprovals} awaiting sign-off`, route: 'signoff-approvals' },
            ],
        };
        const checklistByMode = {
            manager: [
                `Review ${summary.pendingApprovals} pending approvals before end-of-cycle cut-off.`,
                `Triage ${summary.criticalDefects} critical defects affecting release confidence.`,
                `Push ${summary.retestQueue} retest items back into executable paths.`,
            ],
            lead: [
                `Resolve ${summary.blocked} blocked scenarios before the next test wave.`,
                `Confirm retest ownership for ${summary.retestQueue} fixed defects.`,
                `Close approval bottlenecks across ${summary.cycles} active cycles.`,
            ],
            business: [
                `Start with ${summary.pending} scenarios that are still not run.`,
                `Capture evidence for ${summary.fail + summary.blocked} failed or blocked steps.`,
                `Complete ${summary.pendingApprovals} pending business sign-offs.`,
            ],
        };
        const cards = cardsByMode[workspace] || cardsByMode.manager;
        const checklist = checklistByMode[workspace] || checklistByMode.manager;

        return `
            <div class="explore-page" data-testid="role-workspace-page">
                <div class="explore-page__header">
                    <div>
                        ${PGBreadcrumb.html([{ label: 'Programs', onclick: 'App.navigate("programs")' }, { label: 'Test Overview', onclick: 'App.navigate("test-overview")' }, { label: headingMap[workspace] || headingMap.manager }])}
                        <h1 class="explore-page__title">${headingMap[workspace] || headingMap.manager}</h1>
                        <p class="explore-page__subtitle">${subtitleMap[workspace] || subtitleMap.manager}</p>
                    </div>
                </div>
                ${TestingShared.renderModuleNav('test-overview')}
                ${renderKpis(summary)}
                <div class="explore-spotlight-grid" data-testid="role-workspace-grid">
                    ${cards.map((card) => `
                        <button class="explore-spotlight-card" type="button" onclick="App.navigate('${card.route}')">
                            <span class="explore-spotlight-card__eyebrow">Workspace Focus</span>
                            <span class="explore-spotlight-card__title">${esc(card.title)}</span>
                            <span class="explore-spotlight-card__copy">${esc(card.copy)}</span>
                            <span class="explore-spotlight-card__metric">${esc(card.metric)}</span>
                        </button>
                    `).join('')}
                </div>
                <div style="display:grid;grid-template-columns:1.05fr .95fr;gap:var(--exp-space-lg);margin-top:var(--exp-space-lg)">
                    ${renderRoleOperationalBoard(workspace, summary)}
                    ${renderWorkspaceOpsRail(workspace, summary)}
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--exp-space-lg);margin-top:var(--exp-space-lg)">
                    <div class="exp-card">
                        <div class="exp-card__header">Priority Checklist</div>
                        <div class="exp-card__body" data-testid="role-workspace-checklist" style="display:grid;gap:10px">
                            ${checklist.map((item) => `<div class="exp-detail-row"><span class="exp-detail-row__label">${esc(item)}</span></div>`).join('')}
                        </div>
                    </div>
                    <div class="exp-card">
                        <div class="exp-card__header">Quick Actions</div>
                        <div class="exp-card__body" style="display:grid;gap:10px">
                            <button type="button" class="explore-spotlight-card" style="padding:14px" onclick="App.navigate('execution-center')">
                                <span class="explore-spotlight-card__title" style="font-size:14px">Open Execution Center</span>
                                <span class="explore-spotlight-card__metric">${summary.executions}</span>
                            </button>
                            <button type="button" class="explore-spotlight-card" style="padding:14px" onclick="App.navigate('defects-retest')">
                                <span class="explore-spotlight-card__title" style="font-size:14px">Defects & Retest</span>
                                <span class="explore-spotlight-card__metric">${summary.retestQueue}</span>
                            </button>
                            <button type="button" class="explore-spotlight-card" style="padding:14px" onclick="App.navigate('signoff-approvals')">
                                <span class="explore-spotlight-card__title" style="font-size:14px">Approvals & Sign-off</span>
                                <span class="explore-spotlight-card__metric">${summary.pendingApprovals}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async function render(modeOverride = null) {
        const main = document.getElementById('mainContent');
        const pid = TestingShared.getProgram();
        if (!pid) {
            main.innerHTML = TestingShared.noProgramHtml('Test Overview');
            return;
        }

        _pid = pid;
        main.innerHTML = `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`;

        try {
            await fetchAll();
            const summary = aggregate();
            if (modeOverride) {
                main.innerHTML = renderWorkspace(modeOverride, summary);
                return;
            }
            main.innerHTML = `
                <div class="explore-page" data-testid="test-overview-page">
                    <div class="explore-page__header">
                        <div>
                            ${PGBreadcrumb.html([{ label: 'Programs', onclick: 'App.navigate("programs")' }, { label: 'Test Overview' }])}
                            <h1 class="explore-page__title">Test Overview</h1>
                            <p class="explore-page__subtitle">Operations-first landing for execution, defect triage, approvals, and test readiness.</p>
                        </div>
                    </div>
                    ${TestingShared.renderModuleNav('test-overview')}
                    ${renderKpis(summary)}
                    ${renderRoleCockpit(summary)}
                    ${renderFocusGrid(summary)}
                    ${renderActionPanels(summary)}
                    ${renderReleaseReadinessChain(summary)}
                </div>
            `;
        } catch (err) {
            main.innerHTML = `<div class="empty-state"><p>⚠️ ${esc(err.message || 'Failed to load test overview')}</p></div>`;
        }
    }

    return { render };
})();
