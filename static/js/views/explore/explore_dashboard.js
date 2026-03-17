/**
 * Explore Phase — Module E: Dashboard & Analytics
 * F-050: ExploreDashboardPage     F-051: Workshop Completion Burndown
 * F-052: Wave Progress Bars       F-053: Fit/Gap Trend
 * F-054: Requirement Pipeline     F-055: Open Item Aging
 * F-056: Gap Density Heatmap      F-057: Scope Coverage Donut
 *
 * Route: /explore/dashboard (via App.navigate)
 * Uses Chart.js (already loaded via CDN)
 */
const ExploreDashboardView = (() => {
    'use strict';

    const esc = ExpUI.esc;
    let _pid = null;
    let _metrics = null;
    let _snapshots = [];
    let _charts = [];

    function _destroyCharts() { _charts.forEach(c => { try { c.destroy(); } catch {} }); _charts = []; }

    // ── Data fetch ───────────────────────────────────────────────────
    async function fetchData() {
        const [snap, levels, wsStats, reqStats, oiStats, allLevels, coverageMatrix] = await Promise.allSettled([
            ExploreAPI.snapshots.list(_pid, { limit: 30 }),
            ExploreAPI.levels.listL1(_pid),
            ExploreAPI.workshops.stats(_pid),
            ExploreAPI.requirements.stats(_pid),
            ExploreAPI.openItems.stats(_pid),
            API.get(`/explore/process-levels?project_id=${_pid}&flat=true`),
            ExploreAPI.requirements.coverageMatrix(_pid),
        ]);

        _snapshots = snap.status === 'fulfilled' ? (snap.value || []) : [];

        const workshopStats = wsStats.status === 'fulfilled' ? (wsStats.value || {}) : {};
        const wsTotal = workshopStats.total || 0;
        const wsCompleted = workshopStats.completed || 0;
        const wsByWave = workshopStats.by_wave_progress || {};
        const stepsTotal = workshopStats.steps_total || 0;
        const stepsDecided = workshopStats.steps_decided || 0;

        // Compute fit/gap stats from all process levels
        const allPL = allLevels.status === 'fulfilled' ? (allLevels.value?.items || allLevels.value || []) : [];
        const l4steps = allPL.filter(p => p.level === 4);
        const fitByDecision = Object.assign({ fit: 0, gap: 0, partial_fit: 0 }, workshopStats.fit_breakdown || {});

        // If aggregate payload is empty, derive once from flat process levels.
        const fitDecisionTotal = fitByDecision.fit + fitByDecision.gap + fitByDecision.partial_fit;
        if (fitDecisionTotal === 0 && l4steps.length > 0) {
            l4steps.forEach(s => {
                if (s.fit_status === 'fit') fitByDecision.fit++;
                else if (s.fit_status === 'gap') fitByDecision.gap++;
                else if (s.fit_status === 'partial_fit') fitByDecision.partial_fit++;
            });
        }

        _metrics = {
            levels: levels.status === 'fulfilled' ? (levels.value || []) : [],
            allLevels: allPL,
            workshops: { total: wsTotal, completed: wsCompleted, by_wave: wsByWave, steps_total: stepsTotal, steps_decided: stepsDecided },
            requirements: reqStats.status === 'fulfilled' ? (reqStats.value || {}) : {},
            openItems: oiStats.status === 'fulfilled' ? (oiStats.value || {}) : {},
            fitByDecision: fitByDecision,
            coverageMatrix: coverageMatrix.status === 'fulfilled' ? (coverageMatrix.value || {}) : {},
        };
    }

    // ── KPI Strip ────────────────────────────────────────────────────
    function renderKpiStrip() {
        const m = _metrics;
        const wsTotal = m.workshops.total || 0;
        const wsCompleted = m.workshops.completed || 0;
        const wsRate = wsTotal ? Math.round(wsCompleted / wsTotal * 100) : 0;
        const reqTotal = m.requirements.total || 0;
        const oiByStatus = m.openItems.by_status || {};
        const oiOpen = (oiByStatus.open || 0) + (oiByStatus.in_progress || 0) + (oiByStatus.blocked || 0);
        const oiOverdue = m.openItems.overdue_count || 0;

        return `<div class="exp-kpi-strip">
            ${ExpUI.kpiBlock({ value: wsTotal, label: 'Workshops', accent: 'var(--exp-l2)' })}
            ${ExpUI.kpiBlock({ value: wsRate, suffix: '%', label: 'WS Completion', accent: wsRate >= 80 ? 'var(--exp-fit)' : wsRate >= 50 ? '#f59e0b' : 'var(--exp-gap)' })}
            ${ExpUI.kpiBlock({ value: reqTotal, label: 'Requirements', accent: 'var(--exp-requirement)' })}
            ${ExpUI.kpiBlock({ value: oiOpen, label: 'Open Items', accent: 'var(--exp-open-item)' })}
            ${ExpUI.kpiBlock({ value: oiOverdue, label: 'Overdue OIs', accent: oiOverdue > 0 ? 'var(--exp-gap)' : 'var(--exp-fit)' })}
            ${ExpUI.kpiBlock({ value: m.requirements.readiness?.score || 0, suffix: '%', label: 'Go-Live Readiness', accent: (m.requirements.readiness?.score || 0) >= 80 ? 'var(--exp-fit)' : (m.requirements.readiness?.score || 0) >= 50 ? '#f59e0b' : 'var(--exp-gap)' })}
        </div>`;
    }

    // ── F-051: Workshop Completion Burndown ───────────────────────────
    function renderBurndownChart(containerId) {
        if (typeof Chart === 'undefined') return;
        const ctx = document.getElementById(containerId);
        if (!ctx) return;

        let labels, completed, total;
        if (_snapshots.length) {
            labels = _snapshots.map(s => s.snapshot_date).reverse();
            completed = _snapshots.map(s => (s.metrics?.workshops?.completed || 0)).reverse();
            total = _snapshots.map(s => (s.metrics?.workshops?.total || 0)).reverse();
        } else {
            // Fallback: show current status distribution as bar chart
            const m = _metrics.workshops;
            labels = ['Current'];
            completed = [m.completed || 0];
            total = [m.total || 0];
        }

        const c = new Chart(ctx, {
            type: _snapshots.length ? 'line' : 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Completed', data: completed, borderColor: '#30914c', backgroundColor: 'rgba(48,145,76,0.1)', fill: true, tension: 0.3 },
                    { label: 'Total', data: total, borderColor: '#0070f2', borderDash: [5, 5], fill: false, tension: 0.3 },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } }, scales: { y: { beginAtZero: true } } },
        });
        _charts.push(c);
    }

    // ── F-052: Wave Progress Bars ────────────────────────────────────
    function renderWaveProgress() {
        const wsByWave = _metrics.workshops.by_wave || {};
        const waves = Object.keys(wsByWave).sort();
        if (!waves.length) return '<div class="exp-empty"><div class="exp-empty__title">No wave data</div></div>';

        const bars = waves.map(w => {
            const d = wsByWave[w] || {};
            const total = d.total || 1;
            const completed = d.completed || 0;
            const pct = Math.round(completed / total * 100);
            return `<div class="exp-metric-bar">
                <div class="exp-bar-row exp-bar-row--spaced">
                    <span>Wave ${esc(w)}</span><span>${completed}/${total} (${pct}%)</span>
                </div>
                <div class="exp-capacity-bar">
                    <div class="exp-capacity-bar__fill" style="width:${pct}%;background:${pct >= 80 ? 'var(--exp-fit)' : pct >= 50 ? 'var(--exp-partial)' : 'var(--exp-gap)'}"></div>
                </div>
            </div>`;
        }).join('');
        return bars;
    }

    // ── F-053: Fit/Gap Trend ─────────────────────────────────────────
    function renderFitGapTrend(containerId) {
        if (typeof Chart === 'undefined') return;
        const ctx = document.getElementById(containerId);
        if (!ctx) return;

        let labels, fit, gap, partial;
        if (_snapshots.length) {
            labels = _snapshots.map(s => s.snapshot_date).reverse();
            fit = _snapshots.map(s => (s.metrics?.process_steps?.by_decision?.fit || 0)).reverse();
            gap = _snapshots.map(s => (s.metrics?.process_steps?.by_decision?.gap || 0)).reverse();
            partial = _snapshots.map(s => (s.metrics?.process_steps?.by_decision?.partial_fit || 0)).reverse();
        } else {
            // Fallback: show current fit/gap distribution
            const fd = _metrics.fitByDecision || {};
            labels = ['Current'];
            fit = [fd.fit || 0];
            gap = [fd.gap || 0];
            partial = [fd.partial_fit || 0];
        }

        const c = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Fit', data: fit, borderColor: '#30914c', backgroundColor: 'rgba(48,145,76,0.2)', fill: true, tension: 0.3 },
                    { label: 'Gap', data: gap, borderColor: '#e76500', backgroundColor: 'rgba(231,101,0,0.2)', fill: true, tension: 0.3 },
                    { label: 'Partial', data: partial, borderColor: '#0070f2', backgroundColor: 'rgba(0,112,242,0.2)', fill: true, tension: 0.3 },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } }, scales: { y: { stacked: true, beginAtZero: true } } },
        });
        _charts.push(c);
    }

    // ── F-054: Requirement Pipeline Funnel ───────────────────────────
    function renderReqPipeline() {
        const bs = _metrics.requirements.by_status || {};
        const stages = ['draft', 'under_review', 'approved', 'in_backlog', 'realized', 'verified'];
        const colors = ['#a9b4be', '#e76500', '#0070f2', '#6c3483', '#30914c', '#1e8449'];
        const maxVal = Math.max(...stages.map(s => bs[s] || 0), 1);

        return stages.map((s, i) => {
            const v = bs[s] || 0;
            const pct = Math.round(v / maxVal * 100);
            return `<div class="exp-bar-row">
                <span class="exp-bar-row__label">${s.replace(/_/g, ' ')}</span>
                <div class="exp-bar-track">
                    <div class="exp-bar-fill" style="width:${pct}%;background:${colors[i]}"></div>
                </div>
                <span class="exp-bar-row__value">${v}</span>
            </div>`;
        }).join('');
    }

    // ── W-5: Go-Live Readiness Card ─────────────────────────────────
    function renderReadinessCard() {
        const r = _metrics.requirements || {};
        const conv = r.conversion || {};
        const wricef = r.wricef_candidates || {};
        const readiness = r.readiness || {};
        const score = readiness.score || 0;

        // Readiness gauge
        const gaugeColor = score >= 80 ? 'var(--exp-fit)' : score >= 50 ? '#f59e0b' : 'var(--exp-gap)';
        const gaugeAngle = (score / 100) * 180;

        // Conversion stats
        const total = r.total || 0;
        const converted = conv.converted_total || 0;
        const convRate = conv.conversion_rate || 0;

        // Criticality breakdown
        const crit = r.by_criticality || {};
        const critBars = [
            { key: 'business_critical', label: 'Business Critical', color: 'var(--exp-gap)', weight: 3 },
            { key: 'important', label: 'Important', color: '#f59e0b', weight: 2 },
            { key: 'nice_to_have', label: 'Nice to Have', color: 'var(--exp-fit)', weight: 1 },
        ];

        return `
            <div class="exp-readiness-grid">
                <div class="exp-readiness-gauge">
                    <div class="exp-readiness-gauge__frame">
                        <svg viewBox="0 0 160 90">
                            <path d="M 10 80 A 70 70 0 0 1 150 80" fill="none" stroke="#e2e8f0" stroke-width="12" stroke-linecap="round"/>
                            <path d="M 10 80 A 70 70 0 0 1 150 80" fill="none" stroke="${gaugeColor}" stroke-width="12" stroke-linecap="round"
                                stroke-dasharray="${Math.round(gaugeAngle * 70 * Math.PI / 180)} 999" />
                            <text x="80" y="75" text-anchor="middle" font-size="28" font-weight="700" fill="${gaugeColor}">${score}%</text>
                        </svg>
                    </div>
                    <div class="exp-readiness-title">Go-Live Readiness</div>
                    <div class="exp-readiness-sub">
                        Weighted by business criticality
                    </div>
                </div>
                <div>
                    <div class="exp-readiness-section-title">Conversion Coverage</div>
                    <div class="exp-bar-row">
                        <div class="exp-bar-track exp-bar-track--sm">
                            <div class="exp-bar-fill" style="width:${convRate}%;background:var(--exp-decision)"></div>
                        </div>
                        <span class="exp-bar-row__value exp-bar-row__value--wide">${converted}/${total}</span>
                    </div>
                    <div class="exp-readiness-meta">
                        ${conv.with_backlog || 0} WRICEF · ${conv.with_config || 0} Config
                    </div>

                    <div class="exp-readiness-section-title exp-readiness-section-title--tight">WRICEF Candidates</div>
                    <div class="exp-readiness-inline">
                        <span>📋 ${wricef.total || 0} flagged</span>
                        <span class="exp-text-fit">✓ ${wricef.converted || 0} converted</span>
                        <span class="exp-text-gap">⏳ ${wricef.pending || 0} pending</span>
                    </div>
                </div>
            </div>

            <div class="exp-section-divider">
                <div class="exp-readiness-section-title exp-readiness-section-title--tight">By Business Criticality</div>
                ${critBars.map(c => {
                    const v = crit[c.key] || 0;
                    const pct = total ? Math.round(v / total * 100) : 0;
                    return '<div class="exp-bar-row">' +
                        '<span class="exp-bar-row__label exp-bar-row__label--wide">' + c.label + '</span>' +
                        '<div class="exp-bar-track exp-bar-track--xs">' +
                        '<div class="exp-bar-fill" style="width:' + pct + '%;background:' + c.color + '"></div></div>' +
                        '<span class="exp-bar-row__value exp-bar-row__value--wide">' + v + ' (' + pct + '%)</span></div>';
                }).join('')}
            </div>`;
    }

    // ── W-5: Area Coverage Matrix ───────────────────────────────────
    function renderCoverageMatrix() {
        const data = _metrics.coverageMatrix || {};
        const matrix = data.matrix || {};
        const areas = Object.keys(matrix).sort();

        if (!areas.length) return '<div class="exp-empty"><div class="exp-empty__title">No coverage data</div></div>';

        const statuses = ['draft', 'under_review', 'approved', 'in_backlog', 'realized', 'verified'];
        const statusColors = {
            draft: '#a9b4be', under_review: '#e76500', approved: '#0070f2',
            in_backlog: '#6c3483', realized: '#30914c', verified: '#1e8449'
        };

        const coverageClass = (pct) => (
            pct >= 80 ? 'exp-cell-coverage--high'
                : pct >= 50 ? 'exp-cell-coverage--medium'
                    : pct > 0 ? 'exp-cell-coverage--low'
                        : 'exp-cell-coverage--none'
        );

        const header = `<tr>
            <th class="exp-header-compact">Area</th>
            ${statuses.map(s => '<th class="exp-header-compact exp-cell-center">' + s.replace(/_/g, ' ') + '</th>').join('')}
            <th class="exp-header-compact exp-cell-center">Total</th>
            <th class="exp-header-compact exp-cell-center">Converted</th>
            <th class="exp-header-compact exp-cell-center">Coverage</th>
        </tr>`;

        const rows = areas.map(area => {
            const d = matrix[area];
            const total = d.total || 0;
            const converted = d.converted || 0;
            const covPct = total ? Math.round(converted / total * 100) : 0;
            const cells = statuses.map(s => {
                const v = (d.by_status || {})[s] || 0;
                const heatClass = v > 0 ? ` exp-cell-heat--${s}` : '';
                return '<td class="exp-cell-center exp-cell-compact' + (v > 0 ? ' exp-cell-compact--strong' : '') + heatClass + '">' + (v || '—') + '</td>';
            }).join('');

            return '<tr>' +
                '<td class="exp-cell-compact exp-cell-compact--strong">' + esc(area) + '</td>' +
                cells +
                '<td class="exp-cell-center exp-cell-compact exp-cell-compact--strong">' + total + '</td>' +
                '<td class="exp-cell-center exp-cell-compact exp-cell-compact--strong">' + converted + '</td>' +
                '<td class="exp-cell-center exp-cell-compact exp-cell-compact--bold ' + coverageClass(covPct) + '">' + covPct + '%</td>' +
            '</tr>';
        }).join('');

        return '<table class="exp-table exp-table--full"><thead>' + header + '</thead><tbody>' + rows + '</tbody></table>';
    }

    // ── W-5: Impact Distribution Chart ──────────────────────────────
    function renderImpactChart(containerId) {
        if (typeof Chart === 'undefined') return;
        const byImpact = _metrics.requirements.by_impact || {};

        const labels = ['high', 'medium', 'low'];
        const colors = ['#EF4444', '#F59E0B', '#10B981'];
        const data = labels.map(l => byImpact[l] || 0);

        const ctx = document.getElementById(containerId);
        if (!ctx) return;
        const c = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1) + ' Impact'),
                datasets: [{ data, backgroundColor: colors }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: { position: 'bottom', labels: { font: { size: 11 } } },
                },
            },
        });
        _charts.push(c);
    }

    // ── F-055: Open Item Aging ───────────────────────────────────────
    function renderOiAging(containerId) {
        if (typeof Chart === 'undefined') return;
        const aging = _metrics.openItems.by_assignee || {};
        const labels = Object.keys(aging);
        const values = Object.values(aging);

        const ctx = document.getElementById(containerId);
        if (!ctx) return;
        const c = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{ label: 'Open Items', data: values, backgroundColor: '#e76500', borderRadius: 6 }],
            },
            options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } } },
        });
        _charts.push(c);
    }

    // ── F-056: Gap Density Heatmap (simplified table) ────────────────
    function renderGapHeatmap() {
        // group by area × wave — use allLevels (full flat list) for meaningful data
        const levels = (_metrics.allLevels || _metrics.levels || []);
        const areas = [...new Set(levels.map(l => l.process_area_code || l.process_area).filter(Boolean))].sort();
        const waves = [...new Set(levels.map(l => l.wave).filter(Boolean))].sort();

        if (!areas.length || !waves.length) return '<div class="exp-empty"><div class="exp-empty__title">No heatmap data</div></div>';

        const heatData = {};
        for (const l of levels) {
            const area = l.process_area_code || l.process_area;
            if (!area || !l.wave) continue;
            const key = `${area}__${l.wave}`;
            if (!heatData[key]) heatData[key] = { fit: 0, gap: 0, partial: 0, total: 0 };
            heatData[key].total++;
            if (l.fit_status === 'fit') heatData[key].fit++;
            else if (l.fit_status === 'gap') heatData[key].gap++;
            else if (l.fit_status === 'partial_fit') heatData[key].partial++;
        }

        const gapClass = (pct) => (
            pct > 50 ? 'exp-cell-gap--high'
                : pct > 20 ? 'exp-cell-gap--medium'
                    : pct > 0 ? 'exp-cell-gap--low'
                        : 'exp-cell-gap--none'
        );

        const header = `<tr><th></th>${waves.map(w => `<th class="exp-header-compact">W${esc(String(w))}</th>`).join('')}</tr>`;
        const rows = areas.map(a => {
            const cells = waves.map(w => {
                const d = heatData[`${a}__${w}`] || { gap: 0, total: 0 };
                const gapPct = d.total ? Math.round(d.gap / d.total * 100) : 0;
                return `<td class="exp-cell-center exp-cell-compact exp-cell-compact--strong ${gapClass(gapPct)}">${d.gap}/${d.total}</td>`;
            }).join('');
            return `<tr><td class="exp-cell-compact exp-cell-compact--strong">${esc(a)}</td>${cells}</tr>`;
        }).join('');

        return `<table class="exp-table exp-table--full"><thead>${header}</thead><tbody>${rows}</tbody></table>`;
    }

    // ── F-057: Scope Coverage Donut ──────────────────────────────────
    function renderScopeDonut(containerId) {
        if (typeof Chart === 'undefined') return;
        const steps = _metrics.workshops || {};
        const decided = steps.steps_decided || 0;
        const total = steps.steps_total || 0;
        const pending = total - decided;

        const ctx = document.getElementById(containerId);
        if (!ctx) return;
        const c = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Assessed', 'Pending'],
                datasets: [{
                    data: [decided, pending],
                    backgroundColor: ['#30914c', '#a9b4be'],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw} steps` } },
                },
            },
        });
        _charts.push(c);
    }

    // ── Quick Navigation ─────────────────────────────────────────────
    function renderQuickNav() {
        return ExpUI.exploreStageNav({
            current: 'explore-overview',
            actionsHtml: ExpUI.actionButton({ label: 'Capture Snapshot', variant: 'primary', onclick: 'ExploreDashboardView.captureSnapshot()' }),
        });
    }

    function renderWorkflowSpots() {
        const cards = [
            {
                title: 'Scope & Process',
                copy: 'Shape L1-L4 scope, review fit-gap coverage, and surface workshop readiness.',
                metric: `${_metrics.allLevels.filter((item) => item.level === 4).length} steps`,
                action: "App.navigate('explore-scope')",
            },
            {
                title: 'Workshops',
                copy: 'Run the actual Explore sessions and capture fit, gaps, and workshop evidence.',
                metric: `${_metrics.workshops.total || 0} workshops`,
                action: "App.navigate('explore-workshops')",
            },
            {
                title: 'Outcomes',
                copy: 'Review decisions, open items, and requirements as one execution stream.',
                metric: `${(_metrics.requirements.total || 0) + ((_metrics.openItems.by_status?.open || 0) || 0)} active outcomes`,
                action: "App.navigate('explore-outcomes')",
            },
            {
                title: 'Handoff & Traceability',
                copy: 'Convert approved outcomes into backlog items and inspect lineage gaps before Realize.',
                metric: `${_metrics.requirements.approved_without_link || 0} pending handoffs`,
                action: "App.navigate('explore-traceability')",
            },
        ];
        return `<div class="explore-spotlight-grid">
            ${cards.map((card) => `
                <button class="explore-spotlight-card" onclick="${card.action}" type="button">
                    <span class="explore-spotlight-card__eyebrow">Working Area</span>
                    <span class="explore-spotlight-card__title">${esc(card.title)}</span>
                    <span class="explore-spotlight-card__copy">${esc(card.copy)}</span>
                    <span class="explore-spotlight-card__metric">${esc(card.metric)}</span>
                </button>
            `).join('')}
        </div>`;
    }

    async function captureSnapshot() {
        try {
            await ExploreAPI.snapshots.capture(_pid);
            App.toast('Snapshot captured', 'success');
            await fetchData();
            renderPage();
        } catch (err) { App.toast(err.message || 'Failed', 'error'); }
    }

    // ── Main Render (F-050) ──────────────────────────────────────────
    function renderPage() {
        _destroyCharts();
        const main = document.getElementById('mainContent');

        main.innerHTML = `<div class="explore-page" data-testid="explore-overview-page">
            <div class="explore-page__header">
                <div>
                    <h1 class="explore-page__title">Explore Overview</h1>
                    <p class="explore-page__subtitle">Coverage, workshop progress, outcomes, and downstream readiness for Explore.</p>
                </div>
            </div>
            ${renderQuickNav()}
            ${renderKpiStrip()}
            ${renderWorkflowSpots()}

            <div class="exp-dashboard-pair">
                <div class="exp-card"><div class="exp-card__header">Workshop Completion Trend</div><div class="exp-card__body"><canvas id="chartBurndown" height="220"></canvas></div></div>
                <div class="exp-card"><div class="exp-card__header">Fit / Gap / Partial Trend</div><div class="exp-card__body"><canvas id="chartFitGap" height="220"></canvas></div></div>
            </div>

            <div class="exp-dashboard-pair">
                <div class="exp-card"><div class="exp-card__header">Wave Progress</div><div class="exp-card__body">${renderWaveProgress()}</div></div>
                <div class="exp-card"><div class="exp-card__header">Requirement Pipeline</div><div class="exp-card__body">${renderReqPipeline()}</div></div>
            </div>

            <div class="exp-dashboard-pair">
                <div class="exp-card"><div class="exp-card__header">Go-Live Readiness</div><div class="exp-card__body">${renderReadinessCard()}</div></div>
                <div class="exp-card"><div class="exp-card__header">Impact Distribution</div><div class="exp-card__body"><canvas id="chartImpact" height="220"></canvas></div></div>
            </div>

            <div class="exp-card exp-dashboard-card-stack">
                <div class="exp-card__header">Area Coverage Matrix</div>
                <div class="exp-card__body">${renderCoverageMatrix()}</div>
            </div>

            <div class="exp-dashboard-pair">
                <div class="exp-card"><div class="exp-card__header">Open Items by Assignee</div><div class="exp-card__body"><canvas id="chartOiAging" height="220"></canvas></div></div>
                <div class="exp-card"><div class="exp-card__header">Scope Coverage</div><div class="exp-card__body"><canvas id="chartScopeDonut" height="220"></canvas></div></div>
            </div>

            <div class="exp-card exp-dashboard-card-stack">
                <div class="exp-card__header">Gap Density Heatmap (Area × Wave)</div>
                <div class="exp-card__body">${renderGapHeatmap()}</div>
            </div>
        </div>`;

        // Render charts after DOM is ready
        requestAnimationFrame(() => {
            renderBurndownChart('chartBurndown');
            renderFitGapTrend('chartFitGap');
            renderOiAging('chartOiAging');
            renderScopeDonut('chartScopeDonut');
            renderImpactChart('chartImpact');
        });
    }

    async function render() {
        _destroyCharts();
        const main = document.getElementById('mainContent');
        const project = App.getActiveProject();
        if (!project) {
            main.innerHTML = '<div class="exp-empty"><div class="exp-empty__icon">📊</div><div class="exp-empty__title">Select a project first</div></div>';
            return;
        }
        _pid = project.id;
        main.innerHTML = '<div class="explore-page exp-loading-shell"><div class="exp-loading-shell__inner"><div class="exp-loading-shell__icon">⏳</div>Loading dashboard…</div></div>';
        try {
            await fetchData();
            renderPage();
        } catch (err) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
        }
    }

    return { render, captureSnapshot };
})();
