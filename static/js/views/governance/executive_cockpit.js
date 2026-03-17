/**
 * Executive Cockpit
 * Leadership-facing summary for milestones, risk posture, and readiness.
 */
const ExecutiveCockpitView = (() => {
    'use strict';

    const RAG_COLORS = { green: '#30914c', amber: '#e76500', red: '#cc1919' };
    const RAG_ICONS = { green: '●', amber: '●', red: '●' };
    const RAG_LABELS = { green: 'On Track', amber: 'At Risk', red: 'Critical' };
    let _charts = [];

    function esc(value) {
        const d = document.createElement('div');
        d.textContent = value ?? '';
        return d.innerHTML;
    }

    function _destroyCharts() {
        _charts.forEach((chart) => { try { chart.destroy(); } catch (_) {} });
        _charts = [];
    }

    function ragBadge(rag) {
        const color = RAG_COLORS[rag] || '#94a3b8';
        return `<span class="cockpit-rag" style="background:${color}">${RAG_LABELS[rag] || rag || 'Unknown'}</span>`;
    }

    function ragDot(rag) {
        const color = RAG_COLORS[rag] || '#94a3b8';
        return `<span style="color:${color}">${RAG_ICONS[rag] || '●'}</span>`;
    }

    function _projectDisplay(project) {
        if (!project) return '';
        const code = String(project.code || '').trim();
        const name = String(project.name || '').trim();
        const isDefault = code.toUpperCase() === 'DEFAULT'
            || name.toUpperCase() === 'DEFAULT'
            || /(?:^| - )default$/i.test(name);
        if (isDefault) return 'Default';
        return name || code || 'Selected';
    }

    function _kpiValueKind(value) {
        const text = String(value ?? '').replace(/<[^>]+>/g, '').trim();
        if (!text) return 'empty';
        if (/^[-+]?[\d.,]+%?$/.test(text)) return 'numeric';
        if (/^\d+\/\d+$/.test(text)) return 'ratio';
        return 'text';
    }

    function kpiCard(label, value, subtitle, rag) {
        const border = RAG_COLORS[rag] || 'var(--sap-border)';
        const valueKind = _kpiValueKind(value);
        return `
            <div class="cockpit-kpi" style="border-left: 4px solid ${border}">
                <div class="cockpit-kpi__value cockpit-kpi__value--${valueKind}">${value}</div>
                <div class="cockpit-kpi__label">${label}</div>
                ${subtitle ? `<div class="cockpit-kpi__sub">${subtitle}</div>` : ''}
            </div>
        `;
    }

    function areaCard(title, rag, metrics) {
        const rows = metrics.map((metric) => `
            <div class="cockpit-area__row">
                <span class="cockpit-area__metric-label">${metric.label}</span>
                <span class="cockpit-area__metric-value">${metric.value}</span>
            </div>
        `).join('');
        return `
            <div class="cockpit-area-card">
                <div class="cockpit-area__header">
                    <span>${ragDot(rag)}</span>
                    <span class="cockpit-area__title">${title}</span>
                    ${ragBadge(rag)}
                </div>
                <div class="cockpit-area__body">${rows}</div>
            </div>
        `;
    }

    function _renderShell(prog, project, bodyHtml, opts = {}) {
        const projectDisplay = _projectDisplay(project);
        return WorkspaceUI.shell({
            current: 'executive-cockpit',
            testId: 'workspace-executive-page',
            eyebrow: 'Workspace',
            title: 'Executive Cockpit',
            subtitle: 'Fixed leadership summary for steering committees, risk escalation, and milestone governance.',
            breadcrumbs: [{ label: 'Programs', onclick: 'App.navigate("programs")' }, { label: 'Executive Cockpit' }],
            context: {
                program: prog.name,
                project: projectDisplay,
                status: prog.status || 'active',
                phase: opts.phase || 'Program summary',
            },
            actionsHtml: `
                <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="App.navigate('reports')">Open Reports</button>
                <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="App.navigate('dashboard')">Open Operational Dashboard</button>
            `,
            spotlights: opts.spotlights || [
                { value: 'Loading', label: 'Overall Status', sub: 'Resolving leadership summary' },
                { value: project ? projectDisplay : 'Optional', label: 'Project Lens', sub: project ? 'Explore deep-dive will use the active project' : 'Select a project for explore-specific detail' },
                { value: 'Loading', label: 'Go-Live Window', sub: 'Pulling timeline and milestone health' },
                { value: 'Loading', label: 'Exception Areas', sub: 'Loading area-level risk posture' },
            ],
            bodyHtml,
        });
    }

    async function render() {
        _destroyCharts();
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        const project = typeof App.getActiveProject === 'function' ? App.getActiveProject() : null;

        if (!prog) {
            main.innerHTML = PGEmptyState.html({
                icon: 'cockpit',
                title: 'No Program Selected',
                description: 'Select a program to view the executive cockpit.',
                action: { label: 'Go to Programs', onclick: "App.navigate('programs')" },
            });
            return;
        }

        main.innerHTML = _renderShell(prog, project, '<div class="workspace-loading">Loading executive summary…</div>');

        try {
            const [fullRes, exploreRes] = await Promise.allSettled([
                API.get(`/reports/program-health/${prog.id}`),
                project
                    ? API.get(`/reports/program/${prog.id}/health?project_id=${project.id}`)
                    : Promise.resolve(null),
            ]);

            const full = fullRes.status === 'fulfilled' ? fullRes.value : null;
            const explore = exploreRes.status === 'fulfilled' ? exploreRes.value : null;

            if (!full) {
                main.innerHTML = _renderShell(prog, project, PGEmptyState.html({
                    icon: 'warning',
                    title: 'Unable to load metrics',
                    description: 'Health data is not available for this program.',
                }));
                return;
            }

            main.innerHTML = _renderCockpitPage(prog, project, full, explore);
            _renderFitChart(explore);
            _renderTestChart(full.areas?.testing || {});
            _renderDefectChart(full.areas?.testing || {});
        } catch (err) {
            main.innerHTML = _renderShell(prog, project, PGEmptyState.html({
                icon: 'warning',
                title: 'Error Loading Cockpit',
                description: esc(err.message || 'Unknown error'),
            }));
        }
    }

    function _renderCockpitPage(prog, project, full, explore) {
        const areas = full.areas || {};
        const exploreArea = areas.explore || {};
        const backlogArea = areas.backlog || {};
        const testingArea = areas.testing || {};
        const raidArea = areas.raid || {};
        const integrationArea = areas.integration || {};

        const daysToGoLive = full.days_to_go_live;
        const goLiveText = daysToGoLive != null
            ? (daysToGoLive >= 0 ? `${daysToGoLive} days` : `${Math.abs(daysToGoLive)} days overdue`)
            : 'Not set';
        const goLiveRag = daysToGoLive == null
            ? 'green'
            : daysToGoLive < 0
                ? 'red'
                : daysToGoLive < 30
                    ? 'amber'
                    : 'green';

        const phaseLabel = full.current_phase || 'Executive Summary';
        const spotlights = [
            {
                value: RAG_LABELS[full.overall_rag] || 'Unknown',
                label: 'Overall Status',
                sub: `${project ? 'Project-aware' : 'Program-level'} leadership summary`,
            },
            {
                value: goLiveText,
                label: 'Go-Live Window',
                sub: phaseLabel,
            },
            {
                value: `${testingArea.pass_rate || 0}%`,
                label: 'Test Pass Rate',
                sub: `${testingArea.executions || 0} executions logged`,
            },
            {
                value: raidArea.risks_red || 0,
                label: 'Red Risks',
                sub: `${raidArea.actions_overdue || 0} overdue actions`,
            },
        ];

        return _renderShell(
            prog,
            project,
            `
                <div class="workspace-section-stack" data-testid="workspace-executive-summary">
                    <div class="cockpit-kpi-strip">
                        ${kpiCard('Overall Status', `${ragDot(full.overall_rag)} ${RAG_LABELS[full.overall_rag] || 'Unknown'}`, '', full.overall_rag)}
                        ${kpiCard('Go-Live', goLiveText, phaseLabel, goLiveRag)}
                        ${kpiCard('Workshops', `${exploreArea.workshops?.completed || 0}/${exploreArea.workshops?.total || 0}`, `${exploreArea.workshops?.pct || 0}% complete`, exploreArea.rag)}
                        ${kpiCard('Test Pass Rate', `${testingArea.pass_rate || 0}%`, `${testingArea.executions || 0} executions`, testingArea.rag)}
                        ${kpiCard('Open Defects', testingArea.defects?.open ?? 0, `${testingArea.defects?.s1_open || 0} S1 critical`, testingArea.rag)}
                    </div>

                    <div class="cockpit-area-grid">
                        ${areaCard('Explore', exploreArea.rag || 'green', [
                            { label: 'Workshops', value: `${exploreArea.workshops?.completed || 0}/${exploreArea.workshops?.total || 0}` },
                            { label: 'Requirements', value: `${exploreArea.requirements?.approved || 0}/${exploreArea.requirements?.total || 0} approved` },
                            { label: 'Open Items', value: `${exploreArea.open_items?.open || 0} open / ${exploreArea.open_items?.overdue || 0} overdue` },
                        ])}
                        ${areaCard('Backlog / Build', backlogArea.rag || 'green', [
                            { label: 'Items', value: `${backlogArea.items?.done || 0}/${backlogArea.items?.total || 0}` },
                            { label: 'Completion', value: `${backlogArea.items?.pct || 0}%` },
                        ])}
                        ${areaCard('Testing', testingArea.rag || 'green', [
                            { label: 'Test Cases', value: testingArea.test_cases || 0 },
                            { label: 'Pass Rate', value: `${testingArea.pass_rate || 0}%` },
                            { label: 'Open Defects', value: testingArea.defects?.open || 0 },
                            { label: 'S1 Critical', value: testingArea.defects?.s1_open || 0 },
                        ])}
                        ${areaCard('RAID', raidArea.rag || 'green', [
                            { label: 'Open Risks', value: raidArea.risks_open || 0 },
                            { label: 'Red Risks', value: raidArea.risks_red || 0 },
                            { label: 'Overdue Actions', value: raidArea.actions_overdue || 0 },
                            { label: 'Critical Issues', value: raidArea.issues_critical || 0 },
                        ])}
                        ${areaCard('Integration', integrationArea.rag || 'green', [
                            { label: 'Interfaces Live', value: `${integrationArea.interfaces?.live || 0}/${integrationArea.interfaces?.total || 0}` },
                            { label: 'Completion', value: `${integrationArea.interfaces?.pct || 0}%` },
                        ])}
                    </div>

                    ${explore ? _renderExploreDeepDive(explore) : _renderExploreFallback(project)}

                    <div class="cockpit-chart-row">
                        <div class="card cockpit-chart-card">
                            <div class="card-header"><h2>Fit / Gap Distribution</h2></div>
                            <div class="card-body"><canvas id="cockpitFitChart"></canvas></div>
                        </div>
                        <div class="card cockpit-chart-card">
                            <div class="card-header"><h2>Test Results</h2></div>
                            <div class="card-body"><canvas id="cockpitTestChart"></canvas></div>
                        </div>
                        <div class="card cockpit-chart-card">
                            <div class="card-header"><h2>Defect Severity</h2></div>
                            <div class="card-body"><canvas id="cockpitDefectChart"></canvas></div>
                        </div>
                    </div>

                    ${full.phases?.length ? _renderPhaseTimeline(full.phases) : ''}

                    <div class="workspace-panel" data-testid="workspace-executive-actions">
                        <div class="workspace-panel__eyebrow">Drill-down Actions</div>
                        <h2 class="workspace-panel__title">Move from summary to intervention</h2>
                        <p class="workspace-panel__text">
                            The executive cockpit stays summary-first. Use these actions to step into the operational
                            workspace only when the steering conversation needs detail.
                        </p>
                        <div class="workspace-action-buttons">
                            <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="App.navigate('dashboard')">Operational Dashboard</button>
                            <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="App.navigate('explore-outcomes')">Explore Outcomes</button>
                            <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="App.navigate('test-overview')">Test Overview</button>
                            <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="App.navigate('raid')">RAID</button>
                            <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="App.navigate('reports')">Reports Library</button>
                        </div>
                    </div>
                </div>
            `,
            {
                phase: phaseLabel,
                spotlights,
            },
        );
    }

    function _renderExploreDeepDive(explore) {
        const gap = explore.gap_ratio || {};
        const aging = explore.oi_aging || {};
        const coverage = explore.requirement_coverage || {};

        return `
            <div class="card">
                <div class="card-header"><h2>Explore Deep Dive</h2></div>
                <div class="card-body">
                    <div class="cockpit-kpi-strip">
                        ${kpiCard('Gap Ratio', `${gap.gap_pct || 0}%`, `${gap.gap_count || 0} gaps / ${gap.total_steps || 0} steps`, gap.rag)}
                        ${kpiCard('OI Aging', `${aging.avg_age_days || 0} days`, `${aging.overdue || 0} overdue of ${aging.open || 0} open`, aging.rag)}
                        ${kpiCard('Req Coverage', `${coverage.coverage_pct || 0}%`, `${coverage.covered || 0}/${coverage.total || 0} covered`, coverage.rag)}
                        ${kpiCard('Explore RAG', `${ragDot(explore.overall_rag)} ${RAG_LABELS[explore.overall_rag] || 'Unknown'}`, '', explore.overall_rag)}
                    </div>
                </div>
            </div>
        `;
    }

    function _renderExploreFallback(project) {
        return `
            <div class="workspace-message-card">
                ${project
                    ? 'Explore deep-dive is unavailable for the active project right now.'
                    : 'Select an active project to unlock the Explore deep-dive in the executive cockpit.'}
            </div>
        `;
    }

    function _renderPhaseTimeline(phases) {
        const items = phases.map((phase) => {
            const statusClass = phase.status === 'active'
                ? 'cockpit-phase--active'
                : phase.status === 'completed'
                    ? 'cockpit-phase--done'
                    : '';
            const dates = [phase.planned_start, phase.planned_end].filter(Boolean).join(' → ');
            return `
                <div class="cockpit-phase ${statusClass}">
                    <div class="cockpit-phase__name">${esc(phase.name)}</div>
                    <div class="cockpit-phase__bar">
                        <div class="cockpit-phase__fill" style="width:${phase.completion_pct || 0}%"></div>
                    </div>
                    <div class="cockpit-phase__info">${phase.completion_pct || 0}% ${dates ? `· ${dates}` : ''}</div>
                </div>
            `;
        }).join('');

        return `
            <div class="card">
                <div class="card-header"><h2>Phase Timeline</h2></div>
                <div class="card-body cockpit-phases">${items}</div>
            </div>
        `;
    }

    function _renderFitChart(explore) {
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('cockpitFitChart');
        if (!canvas || !explore?.fit_distribution) return;

        const fitDistribution = explore.fit_distribution;
        const chart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Fit', 'Gap', 'Partial Fit', 'Pending'],
                datasets: [{
                    data: [
                        fitDistribution.fit || 0,
                        fitDistribution.gap || 0,
                        fitDistribution.partial_fit || 0,
                        fitDistribution.pending || 0,
                    ],
                    backgroundColor: ['#30914c', '#cc1919', '#e76500', '#d9d9d9'],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } },
            },
        });
        _charts.push(chart);
    }

    function _renderTestChart(testingArea) {
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('cockpitTestChart');
        if (!canvas) return;

        const executionTotal = testingArea.executions || 0;
        const passRate = testingArea.pass_rate || 0;
        const passCount = Math.round((executionTotal * passRate) / 100);
        const failCount = executionTotal - passCount;

        const chart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Pass', 'Fail / Other'],
                datasets: [{
                    data: [passCount, failCount],
                    backgroundColor: ['#30914c', '#cc1919'],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } },
            },
        });
        _charts.push(chart);
    }

    function _renderDefectChart(testingArea) {
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('cockpitDefectChart');
        if (!canvas || !testingArea.defects) return;

        const s1 = testingArea.defects.s1_open || 0;
        const open = testingArea.defects.open || 0;
        const closed = (testingArea.defects.total || 0) - open;

        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['S1 Critical', 'Other Open', 'Closed'],
                datasets: [{
                    data: [s1, open - s1, closed],
                    backgroundColor: ['#cc1919', '#e76500', '#30914c'],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            },
        });
        _charts.push(chart);
    }

    return { render };
})();
