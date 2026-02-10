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
        const [snap, levels, wsStats, reqStats, oiStats] = await Promise.allSettled([
            ExploreAPI.snapshots.list(_pid, { limit: 30 }),
            ExploreAPI.levels.listL1(_pid),
            ExploreAPI.workshops.stats(_pid),
            ExploreAPI.requirements.stats(_pid),
            ExploreAPI.openItems.stats(_pid),
        ]);

        _snapshots = snap.status === 'fulfilled' ? (snap.value || []) : [];

        _metrics = {
            levels: levels.status === 'fulfilled' ? (levels.value || []) : [],
            workshops: wsStats.status === 'fulfilled' ? (wsStats.value || {}) : {},
            requirements: reqStats.status === 'fulfilled' ? (reqStats.value || {}) : {},
            openItems: oiStats.status === 'fulfilled' ? (oiStats.value || {}) : {},
        };
    }

    // ── KPI Strip ────────────────────────────────────────────────────
    function renderKpiStrip() {
        const m = _metrics;
        const wsTotal = m.workshops.total || 0;
        const wsCompleted = m.workshops.completed || 0;
        const wsRate = wsTotal ? Math.round(wsCompleted / wsTotal * 100) : 0;
        const reqTotal = m.requirements.total || 0;
        const oiOpen = m.openItems.open_count || m.openItems.overdue_count || 0;
        const oiOverdue = m.openItems.overdue_count || 0;

        return `<div class="exp-kpi-strip">
            ${ExpUI.kpiBlock({ value: wsTotal, label: 'Workshops', icon: '📋' })}
            ${ExpUI.kpiBlock({ value: wsRate + '%', label: 'WS Completion', accent: wsRate >= 80 ? 'var(--exp-fit)' : wsRate >= 50 ? 'var(--exp-partial)' : 'var(--exp-gap)' })}
            ${ExpUI.kpiBlock({ value: reqTotal, label: 'Requirements', icon: '📝' })}
            ${ExpUI.kpiBlock({ value: oiOpen, label: 'Open Items', accent: 'var(--exp-open-item)' })}
            ${ExpUI.kpiBlock({ value: oiOverdue, label: 'Overdue OIs', accent: oiOverdue > 0 ? 'var(--exp-gap)' : 'var(--exp-fit)', icon: oiOverdue > 0 ? '🔴' : '✅' })}
        </div>`;
    }

    // ── F-051: Workshop Completion Burndown ───────────────────────────
    function renderBurndownChart(containerId) {
        if (!_snapshots.length || typeof Chart === 'undefined') return;
        const labels = _snapshots.map(s => s.snapshot_date).reverse();
        const completed = _snapshots.map(s => (s.metrics?.workshops?.completed || 0)).reverse();
        const total = _snapshots.map(s => (s.metrics?.workshops?.total || 0)).reverse();

        const ctx = document.getElementById(containerId);
        if (!ctx) return;
        const c = new Chart(ctx, {
            type: 'line',
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
        if (!_snapshots.length || typeof Chart === 'undefined') return;
        const labels = _snapshots.map(s => s.snapshot_date).reverse();
        const fit = _snapshots.map(s => (s.metrics?.process_steps?.by_decision?.fit || 0)).reverse();
        const gap = _snapshots.map(s => (s.metrics?.process_steps?.by_decision?.gap || 0)).reverse();
        const partial = _snapshots.map(s => (s.metrics?.process_steps?.by_decision?.partial_fit || 0)).reverse();

        const ctx = document.getElementById(containerId);
        if (!ctx) return;
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
        // group by area × wave
        const levels = _metrics.levels || [];
        const areas = [...new Set(levels.map(l => l.process_area).filter(Boolean))].sort();
        const waves = [...new Set(levels.map(l => l.wave).filter(Boolean))].sort();

        if (!areas.length || !waves.length) return '<div class="exp-empty"><div class="exp-empty__title">No heatmap data</div></div>';

        const heatData = {};
        for (const l of levels) {
            const key = `${l.process_area}__${l.wave}`;
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
