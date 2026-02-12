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
        const [snap, levels, wsList, reqStats, oiStats, allLevels, coverageMatrix] = await Promise.allSettled([
            ExploreAPI.snapshots.list(_pid, { limit: 30 }),
            ExploreAPI.levels.listL1(_pid),
            ExploreAPI.workshops.list(_pid),
            ExploreAPI.requirements.stats(_pid),
            ExploreAPI.openItems.stats(_pid),
            API.get(`/explore/process-levels?project_id=${_pid}&flat=true`),
            ExploreAPI.requirements.coverageMatrix(_pid),
        ]);

        _snapshots = snap.status === 'fulfilled' ? (snap.value || []) : [];

        // Compute workshop stats from the list
        const workshops = wsList.status === 'fulfilled' ? (wsList.value || []) : [];
        const wsTotal = workshops.length;
        const wsCompleted = workshops.filter(w => w.status === 'completed').length;
        const wsByWave = {};
        workshops.forEach(w => {
            const wave = w.wave || 'unassigned';
            if (!wsByWave[wave]) wsByWave[wave] = { total: 0, completed: 0 };
            wsByWave[wave].total++;
            if (w.status === 'completed') wsByWave[wave].completed++;
        });
        const stepsTotal = workshops.reduce((s, w) => s + (w.steps_total || 0), 0);
        const stepsDecided = workshops.reduce((s, w) => s + (w.fit_count || 0) + (w.gap_count || 0) + (w.partial_count || 0), 0);

        // Compute fit/gap stats from all process levels
        const allPL = allLevels.status === 'fulfilled' ? (allLevels.value?.items || allLevels.value || []) : [];
        const l4steps = allPL.filter(p => p.level === 4);
        const fitByDecision = { fit: 0, gap: 0, partial_fit: 0 };
        l4steps.forEach(s => {
            if (s.fit_status === 'fit') fitByDecision.fit++;
            else if (s.fit_status === 'gap') fitByDecision.gap++;
            else if (s.fit_status === 'partial_fit') fitByDecision.partial_fit++;
        });

        // If L4 levels are all pending, use workshop-level aggregated counts
        const fitDecisionTotal = fitByDecision.fit + fitByDecision.gap + fitByDecision.partial_fit;
        if (fitDecisionTotal === 0 && workshops.length > 0) {
            fitByDecision.fit = workshops.reduce((s, w) => s + (w.fit_count || 0), 0);
            fitByDecision.gap = workshops.reduce((s, w) => s + (w.gap_count || 0), 0);
            fitByDecision.partial_fit = workshops.reduce((s, w) => s + (w.partial_count || 0), 0);
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
            return `<div style="margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
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
            return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                <span style="width:90px;font-size:12px;text-align:right">${s.replace(/_/g, ' ')}</span>
                <div style="flex:1;height:22px;background:#f0f0f0;border-radius:4px;overflow:hidden">
                    <div style="width:${pct}%;height:100%;background:${colors[i]};border-radius:4px;transition:width .3s"></div>
                </div>
                <span style="width:30px;font-size:12px;font-weight:600">${v}</span>
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
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
                <!-- Left: Readiness Score -->
                <div style="text-align:center">
                    <div style="position:relative;width:160px;height:90px;margin:0 auto 12px">
                        <svg viewBox="0 0 160 90" style="width:100%;height:100%">
                            <path d="M 10 80 A 70 70 0 0 1 150 80" fill="none" stroke="#e2e8f0" stroke-width="12" stroke-linecap="round"/>
                            <path d="M 10 80 A 70 70 0 0 1 150 80" fill="none" stroke="${gaugeColor}" stroke-width="12" stroke-linecap="round"
                                stroke-dasharray="${Math.round(gaugeAngle * 70 * Math.PI / 180)} 999" />
                            <text x="80" y="75" text-anchor="middle" font-size="28" font-weight="700" fill="${gaugeColor}">${score}%</text>
                        </svg>
                    </div>
                    <div style="font-size:13px;font-weight:600;color:var(--sap-text-primary)">Go-Live Readiness</div>
                    <div style="font-size:11px;color:var(--sap-text-secondary);margin-top:4px">
                        Weighted by business criticality
                    </div>
                </div>
                <!-- Right: Conversion Stats -->
                <div>
                    <div style="font-size:13px;font-weight:600;margin-bottom:12px">Conversion Coverage</div>
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                        <div style="flex:1;height:20px;background:#f0f0f0;border-radius:4px;overflow:hidden">
                            <div style="width:${convRate}%;height:100%;background:var(--exp-decision);border-radius:4px;transition:width .3s"></div>
                        </div>
                        <span style="font-size:12px;font-weight:600;min-width:45px">${converted}/${total}</span>
                    </div>
                    <div style="font-size:11px;color:var(--sap-text-secondary);margin-bottom:16px">
                        ${conv.with_backlog || 0} WRICEF · ${conv.with_config || 0} Config
                    </div>

                    <div style="font-size:13px;font-weight:600;margin-bottom:8px">WRICEF Candidates</div>
                    <div style="display:flex;gap:12px;font-size:12px">
                        <span>📋 ${wricef.total || 0} flagged</span>
                        <span style="color:var(--exp-fit)">✓ ${wricef.converted || 0} converted</span>
                        <span style="color:var(--exp-gap)">⏳ ${wricef.pending || 0} pending</span>
                    </div>
                </div>
            </div>

            <!-- Criticality Breakdown -->
            <div style="margin-top:20px;padding-top:16px;border-top:1px solid #e2e8f0">
                <div style="font-size:13px;font-weight:600;margin-bottom:10px">By Business Criticality</div>
                ${critBars.map(c => {
                    const v = crit[c.key] || 0;
                    const pct = total ? Math.round(v / total * 100) : 0;
                    return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
                        '<span style="width:120px;font-size:12px;text-align:right">' + c.label + '</span>' +
                        '<div style="flex:1;height:16px;background:#f0f0f0;border-radius:4px;overflow:hidden">' +
                        '<div style="width:' + pct + '%;height:100%;background:' + c.color + ';border-radius:4px"></div></div>' +
                        '<span style="width:40px;font-size:12px;font-weight:600">' + v + ' (' + pct + '%)</span></div>';
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

        const header = `<tr>
            <th style="font-size:11px">Area</th>
            ${statuses.map(s => '<th style="font-size:11px;text-align:center">' + s.replace(/_/g, ' ') + '</th>').join('')}
            <th style="font-size:11px;text-align:center">Total</th>
            <th style="font-size:11px;text-align:center">Converted</th>
            <th style="font-size:11px;text-align:center">Coverage</th>
        </tr>`;

        const rows = areas.map(area => {
            const d = matrix[area];
            const total = d.total || 0;
            const converted = d.converted || 0;
            const covPct = total ? Math.round(converted / total * 100) : 0;
            const covColor = covPct >= 80 ? 'var(--exp-fit)' : covPct >= 50 ? '#f59e0b' : covPct > 0 ? 'var(--exp-gap)' : '#a9b4be';

            const cells = statuses.map(s => {
                const v = (d.by_status || {})[s] || 0;
                const bg = v > 0 ? statusColors[s] + '18' : '';
                return '<td style="text-align:center;font-size:12px;font-weight:' + (v > 0 ? '600' : '400') + ';background:' + bg + '">' + (v || '—') + '</td>';
            }).join('');

            return '<tr>' +
                '<td style="font-size:12px;font-weight:600;padding:6px">' + esc(area) + '</td>' +
                cells +
                '<td style="text-align:center;font-size:12px;font-weight:600">' + total + '</td>' +
                '<td style="text-align:center;font-size:12px;font-weight:600">' + converted + '</td>' +
                '<td style="text-align:center;font-weight:700;color:' + covColor + '">' + covPct + '%</td>' +
            '</tr>';
        }).join('');

        return '<table class="exp-table" style="width:100%"><thead>' + header + '</thead><tbody>' + rows + '</tbody></table>';
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

        const header = `<tr><th></th>${waves.map(w => `<th style="font-size:11px">W${esc(String(w))}</th>`).join('')}</tr>`;
        const rows = areas.map(a => {
            const cells = waves.map(w => {
                const d = heatData[`${a}__${w}`] || { gap: 0, total: 0 };
                const gapPct = d.total ? Math.round(d.gap / d.total * 100) : 0;
                const bg = gapPct > 50 ? 'var(--exp-gap-bg)' : gapPct > 20 ? 'var(--exp-partial-bg)' : gapPct > 0 ? '#fff8e1' : 'var(--exp-fit-bg)';
                const color = gapPct > 50 ? 'var(--exp-gap)' : gapPct > 20 ? 'var(--exp-partial)' : 'var(--exp-fit)';
                return `<td style="text-align:center;background:${bg};color:${color};font-size:12px;font-weight:600;padding:6px">${d.gap}/${d.total}</td>`;
            }).join('');
            return `<tr><td style="font-size:12px;font-weight:600;padding:6px">${esc(a)}</td>${cells}</tr>`;
        }).join('');

        return `<table class="exp-table" style="width:100%"><thead>${header}</thead><tbody>${rows}</tbody></table>`;
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
        return `<div style="display:flex;flex-wrap:wrap;gap:8px">
            ${ExpUI.actionButton({ label: '🏗️ Hierarchy', variant: 'secondary', onclick: "App.navigate('explore-hierarchy')" })}
            ${ExpUI.actionButton({ label: '📋 Workshops', variant: 'secondary', onclick: "App.navigate('explore-workshops')" })}
            ${ExpUI.actionButton({ label: '📝 Requirements', variant: 'secondary', onclick: "App.navigate('explore-requirements')" })}
            ${ExpUI.actionButton({ label: '📸 Capture Snapshot', variant: 'primary', onclick: 'ExploreDashboardView.captureSnapshot()' })}
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

        main.innerHTML = `<div class="explore-page">
            <div class="explore-page__header">
                <div>
                    <h1 class="explore-page__title">Explore Phase Dashboard</h1>
                    <p class="explore-page__subtitle">Analytics, trends, and reporting for the Explore phase</p>
                </div>
            </div>

            ${renderKpiStrip()}
            ${renderQuickNav()}

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--exp-space-lg);margin-top:var(--exp-space-lg)">
                <div class="exp-card"><div class="exp-card__header">Workshop Completion Trend</div><div class="exp-card__body"><canvas id="chartBurndown" height="220"></canvas></div></div>
                <div class="exp-card"><div class="exp-card__header">Fit / Gap / Partial Trend</div><div class="exp-card__body"><canvas id="chartFitGap" height="220"></canvas></div></div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--exp-space-lg);margin-top:var(--exp-space-lg)">
                <div class="exp-card"><div class="exp-card__header">Wave Progress</div><div class="exp-card__body">${renderWaveProgress()}</div></div>
                <div class="exp-card"><div class="exp-card__header">Requirement Pipeline</div><div class="exp-card__body">${renderReqPipeline()}</div></div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--exp-space-lg);margin-top:var(--exp-space-lg)">
                <div class="exp-card"><div class="exp-card__header">Go-Live Readiness</div><div class="exp-card__body">${renderReadinessCard()}</div></div>
                <div class="exp-card"><div class="exp-card__header">Impact Distribution</div><div class="exp-card__body"><canvas id="chartImpact" height="220"></canvas></div></div>
            </div>

            <div class="exp-card" style="margin-top:var(--exp-space-lg)">
                <div class="exp-card__header">Area Coverage Matrix</div>
                <div class="exp-card__body">${renderCoverageMatrix()}</div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--exp-space-lg);margin-top:var(--exp-space-lg)">
                <div class="exp-card"><div class="exp-card__header">Open Items by Assignee</div><div class="exp-card__body"><canvas id="chartOiAging" height="220"></canvas></div></div>
                <div class="exp-card"><div class="exp-card__header">Scope Coverage</div><div class="exp-card__body"><canvas id="chartScopeDonut" height="220"></canvas></div></div>
            </div>

            <div class="exp-card" style="margin-top:var(--exp-space-lg)">
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
        const prog = App.getActiveProgram();
        if (!prog) {
            main.innerHTML = '<div class="exp-empty"><div class="exp-empty__icon">📊</div><div class="exp-empty__title">Select a program first</div></div>';
            return;
        }
        _pid = prog.id;
        main.innerHTML = '<div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:300px"><div style="text-align:center;color:var(--sap-text-secondary)"><div style="font-size:28px;margin-bottom:8px">⏳</div>Loading dashboard…</div></div>';
        try {
            await fetchData();
            renderPage();
        } catch (err) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
        }
    }

    return { render, captureSnapshot };
})();
