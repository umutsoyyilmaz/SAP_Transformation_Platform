/**
 * SAP Transformation Platform — WR-3.2
 * Executive Cockpit View
 *
 * Single-page executive dashboard showing all KPIs:
 *   - Overall RAG + days to go-live
 *   - Area RAG cards (Explore, Backlog, Testing, RAID, Integration)
 *   - Explore deep-dive: gap ratio, OI aging, requirement coverage
 *   - Charts: fit distribution donut, test pass rate, defect severity
 *
 * Route: App.navigate('executive-cockpit')
 * API:   GET /api/v1/reports/program-health/<pid>
 *         GET /api/v1/reports/program/<pid>/health
 */
const ExecutiveCockpitView = (() => {
    'use strict';

    const esc = (s) => {
        const d = document.createElement('div');
        d.textContent = s ?? '';
        return d.innerHTML;
    };

    let _charts = [];
    function _destroyCharts() {
        _charts.forEach(c => { try { c.destroy(); } catch {} });
        _charts = [];
    }

    // ── RAG helpers ─────────────────────────────────────────────────
    const RAG_COLORS = { green: '#30914c', amber: '#e76500', red: '#cc1919' };
    const RAG_ICONS  = { green: '🟢', amber: '🟡', red: '🔴' };
    const RAG_LABELS = { green: 'On Track', amber: 'At Risk', red: 'Critical' };

    function ragBadge(rag) {
        const c = RAG_COLORS[rag] || '#999';
        return `<span class="cockpit-rag" style="background:${c}">${RAG_LABELS[rag] || rag}</span>`;
    }

    function ragDot(rag) {
        return RAG_ICONS[rag] || '⚪';
    }

    // ── KPI card HTML ───────────────────────────────────────────────
    function kpiCard(label, value, subtitle, rag) {
        const border = RAG_COLORS[rag] || 'var(--sap-border)';
        return `
            <div class="cockpit-kpi" style="border-left: 4px solid ${border}">
                <div class="cockpit-kpi__value">${value}</div>
                <div class="cockpit-kpi__label">${label}</div>
                ${subtitle ? `<div class="cockpit-kpi__sub">${subtitle}</div>` : ''}
            </div>`;
    }

    // ── Area card HTML ──────────────────────────────────────────────
    function areaCard(title, rag, metrics) {
        const rows = metrics.map(m =>
            `<div class="cockpit-area__row">
                <span class="cockpit-area__metric-label">${m.label}</span>
                <span class="cockpit-area__metric-value">${m.value}</span>
            </div>`
        ).join('');
        return `
            <div class="cockpit-area-card">
                <div class="cockpit-area__header">
                    <span>${ragDot(rag)}</span>
                    <span class="cockpit-area__title">${title}</span>
                    ${ragBadge(rag)}
                </div>
                <div class="cockpit-area__body">${rows}</div>
            </div>`;
    }

    // ── Main render ─────────────────────────────────────────────────
    async function render() {
        _destroyCharts();
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();

        if (!prog) {
            main.innerHTML = PGEmptyState.html({ icon: 'cockpit', title: 'No Program Selected', description: 'Select a program to view the executive cockpit.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Executive Cockpit' }])}
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <h2 class="pg-view-title">Executive Cockpit</h2>
                    <span class="badge badge-${esc(prog.status)}">${esc(prog.name)}</span>
                </div>
            </div>
            <div class="cockpit-loading">
                <div class="spinner"></div>
                <p>Loading executive metrics…</p>
            </div>`;

        try {
            const [fullRes, exploreRes] = await Promise.allSettled([
                API.get(`/reports/program-health/${prog.id}`),
                API.get(`/reports/program/${prog.id}/health`),
            ]);

            const full = fullRes.status === 'fulfilled' ? fullRes.value : null;
            const explore = exploreRes.status === 'fulfilled' ? exploreRes.value : null;

            if (!full) {
                main.innerHTML = PGEmptyState.html({ icon: 'warning', title: 'Unable to load metrics', description: 'Health data is not available for this program.' });
                return;
            }

            _renderCockpit(main, prog, full, explore);

        } catch (err) {
            main.innerHTML = PGEmptyState.html({ icon: 'warning', title: 'Error Loading Cockpit', description: esc(err.message || 'Unknown error') });
        }
    }

    function _renderCockpit(main, prog, full, explore) {
        const a = full.areas || {};
        const exp = a.explore || {};
        const bkl = a.backlog || {};
        const tst = a.testing || {};
        const raid = a.raid || {};
        const intg = a.integration || {};

        // Go-live info
        const daysToGoLive = full.days_to_go_live;
        const goLiveText = daysToGoLive != null
            ? (daysToGoLive >= 0 ? `${daysToGoLive} days` : `${Math.abs(daysToGoLive)} days overdue`)
            : 'Not set';
        const goLiveRag = daysToGoLive == null ? 'green'
            : daysToGoLive < 0 ? 'red'
            : daysToGoLive < 30 ? 'amber' : 'green';

        // Phase info
        const currentPhase = full.current_phase || 'N/A';

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Executive Cockpit' }])}
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <h2 class="pg-view-title">Executive Cockpit</h2>
                    <span class="badge badge-${esc(prog.status)}">${esc(prog.name)}</span>
                </div>
            </div>

            <!-- Top KPI strip -->
            <div class="cockpit-kpi-strip">
                ${kpiCard('Overall Status', ragDot(full.overall_rag) + ' ' + RAG_LABELS[full.overall_rag], '', full.overall_rag)}
                ${kpiCard('Go-Live', goLiveText, currentPhase, goLiveRag)}
                ${kpiCard('Workshops', (exp.workshops?.completed || 0) + '/' + (exp.workshops?.total || 0),
                    (exp.workshops?.pct || 0) + '% complete', exp.rag)}
                ${kpiCard('Test Pass Rate', (tst.pass_rate || 0) + '%',
                    (tst.executions || 0) + ' executions', tst.rag)}
                ${kpiCard('Open Defects', tst.defects?.open ?? 0,
                    (tst.defects?.s1_open || 0) + ' S1 critical', tst.rag)}
            </div>

            <!-- Area RAG cards -->
            <div class="cockpit-area-grid">
                ${areaCard('Explore Phase', exp.rag || 'green', [
                    { label: 'Workshops', value: `${exp.workshops?.completed||0}/${exp.workshops?.total||0} (${exp.workshops?.pct||0}%)` },
                    { label: 'Requirements', value: `${exp.requirements?.approved||0}/${exp.requirements?.total||0} approved` },
                    { label: 'Open Items', value: `${exp.open_items?.open||0} open, ${exp.open_items?.overdue||0} overdue` },
                ])}
                ${areaCard('Backlog / Build', bkl.rag || 'green', [
                    { label: 'Items', value: `${bkl.items?.done||0}/${bkl.items?.total||0} done` },
                    { label: 'Completion', value: `${bkl.items?.pct||0}%` },
                ])}
                ${areaCard('Testing', tst.rag || 'green', [
                    { label: 'Test Cases', value: tst.test_cases || 0 },
                    { label: 'Pass Rate', value: `${tst.pass_rate||0}%` },
                    { label: 'Defects', value: `${tst.defects?.open||0} open / ${tst.defects?.total||0} total` },
                    { label: 'S1 Critical', value: tst.defects?.s1_open || 0 },
                ])}
                ${areaCard('RAID', raid.rag || 'green', [
                    { label: 'Risks Open', value: raid.risks_open || 0 },
                    { label: 'Risks Red', value: raid.risks_red || 0 },
                    { label: 'Actions Overdue', value: raid.actions_overdue || 0 },
                    { label: 'Issues Critical', value: raid.issues_critical || 0 },
                ])}
                ${areaCard('Integration', intg.rag || 'green', [
                    { label: 'Interfaces', value: `${intg.interfaces?.live||0}/${intg.interfaces?.total||0} live` },
                    { label: 'Completion', value: `${intg.interfaces?.pct||0}%` },
                ])}
            </div>

            <!-- Explore deep-dive from ExploreMetrics -->
            ${explore ? _renderExploreDeepDive(explore) : ''}

            <!-- Charts row -->
            <div class="cockpit-chart-row">
                <div class="card cockpit-chart-card">
                    <div class="card-header"><h2>Fit/Gap Distribution</h2></div>
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

            <!-- Phase timeline -->
            ${full.phases?.length ? _renderPhaseTimeline(full.phases) : ''}

            <!-- Quick actions -->
            <div class="card" style="margin-top:16px">
                <div class="card-header"><h2>Quick Actions</h2></div>
                <div class="card-body" style="display:flex;gap:8px;flex-wrap:wrap">
                    <button class="btn btn-secondary" onclick="App.navigate('explore-dashboard')">📊 Explore Dashboard</button>
                    <button class="btn btn-secondary" onclick="App.navigate('test-execution')">▶️ Test Execution</button>
                    <button class="btn btn-secondary" onclick="App.navigate('defect-management')">🐛 Defect Management</button>
                    <button class="btn btn-secondary" onclick="App.navigate('raid')">⚠️ RAID</button>
                    <button class="btn btn-secondary" onclick="App.navigate('reports')">📈 Reports</button>
                </div>
            </div>
        `;

        // Render charts
        _renderFitChart(explore);
        _renderTestChart(tst);
        _renderDefectChart(tst);
    }

    // ── Explore deep-dive section ───────────────────────────────────
    function _renderExploreDeepDive(explore) {
        const gr = explore.gap_ratio || {};
        const oi = explore.oi_aging || {};
        const rc = explore.requirement_coverage || {};

        return `
            <div class="card" style="margin-top:16px">
                <div class="card-header"><h2>Explore Phase — Deep Dive</h2></div>
                <div class="card-body">
                    <div class="cockpit-kpi-strip">
                        ${kpiCard('Gap Ratio', (gr.gap_pct || 0) + '%',
                            `${gr.gap_count||0} gaps / ${gr.total_steps||0} steps`, gr.rag)}
                        ${kpiCard('OI Aging', (oi.avg_age_days || 0) + ' days avg',
                            `${oi.overdue||0} overdue of ${oi.open||0} open`, oi.rag)}
                        ${kpiCard('Req Coverage', (rc.coverage_pct || 0) + '%',
                            `${rc.covered||0}/${rc.total||0} covered`, rc.rag)}
                        ${kpiCard('Overall Explore', ragDot(explore.overall_rag) + ' ' + RAG_LABELS[explore.overall_rag],
                            '', explore.overall_rag)}
                    </div>
                </div>
            </div>`;
    }

    // ── Phase timeline ──────────────────────────────────────────────
    function _renderPhaseTimeline(phases) {
        const items = phases.map(p => {
            const statusClass = p.status === 'active' ? 'cockpit-phase--active'
                : p.status === 'completed' ? 'cockpit-phase--done' : '';
            const dates = [p.planned_start, p.planned_end].filter(Boolean).join(' → ');
            return `
                <div class="cockpit-phase ${statusClass}">
                    <div class="cockpit-phase__name">${esc(p.name)}</div>
                    <div class="cockpit-phase__bar">
                        <div class="cockpit-phase__fill" style="width:${p.completion_pct || 0}%"></div>
                    </div>
                    <div class="cockpit-phase__info">${p.completion_pct || 0}% ${dates ? '· ' + dates : ''}</div>
                </div>`;
        }).join('');
        return `
            <div class="card" style="margin-top:16px">
                <div class="card-header"><h2>Phase Timeline</h2></div>
                <div class="card-body cockpit-phases">${items}</div>
            </div>`;
    }

    // ── Charts ──────────────────────────────────────────────────────
    function _renderFitChart(explore) {
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('cockpitFitChart');
        if (!canvas || !explore?.fit_distribution) return;

        const fd = explore.fit_distribution;
        const data = {
            labels: ['Fit', 'Gap', 'Partial Fit', 'Pending'],
            datasets: [{
                data: [fd.fit || 0, fd.gap || 0, fd.partial_fit || 0, fd.pending || 0],
                backgroundColor: ['#30914c', '#cc1919', '#e76500', '#d9d9d9'],
            }]
        };
        const chart = new Chart(canvas, {
            type: 'doughnut',
            data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { font: { size: 11 } } },
                },
            },
        });
        _charts.push(chart);
    }

    function _renderTestChart(tst) {
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('cockpitTestChart');
        if (!canvas) return;

        const execTotal = tst.executions || 0;
        const passRate = tst.pass_rate || 0;
        const passCount = Math.round(execTotal * passRate / 100);
        const failCount = execTotal - passCount;

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
                plugins: {
                    legend: { position: 'bottom', labels: { font: { size: 11 } } },
                },
            },
        });
        _charts.push(chart);
    }

    function _renderDefectChart(tst) {
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById('cockpitDefectChart');
        if (!canvas || !tst.defects) return;

        const s1 = tst.defects.s1_open || 0;
        const open = tst.defects.open || 0;
        const closed = (tst.defects.total || 0) - open;

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
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } },
                },
            },
        });
        _charts.push(chart);
    }

    return { render };
})();
