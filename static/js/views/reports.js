const ReportsView = (() => {
    let healthData = null;
    let presets = [];
    let activeTab = 'health';
    let chartInstances = [];

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    const RAG_COLORS = { green: '#27AE60', amber: '#F39C12', red: '#E74C3C' };
    const RAG_LABELS = { green: 'On Track', amber: 'At Risk', red: 'Critical' };
    const CATEGORY_LABELS = {
        coverage: '📊 Coverage', execution: '▶️ Execution', defect: '🐛 Defect',
        traceability: '🔗 Traceability', ai_insights: '🤖 AI Insights',
        plan: '📋 Plan/Release', custom: '⚙️ Custom'
    };
    const CATEGORY_KEYS = ['coverage', 'execution', 'defect', 'traceability', 'ai_insights', 'plan'];

    function ragBadge(rag) {
        return PGStatusRegistry.badge(rag, { label: RAG_LABELS[rag] || rag || '—' });
    }

    function pctBar(pct, color) {
        return `<div style="background:#e9ecef;border-radius:4px;height:8px;width:120px;display:inline-block;vertical-align:middle;margin-left:8px">
            <div style="background:${color || '#0070f3'};height:100%;width:${Math.min(pct, 100)}%;border-radius:4px"></div>
        </div> <span style="font-size:13px;color:#666">${pct}%</span>`;
    }

    function _destroyCharts() {
        chartInstances.forEach(c => { try { c.destroy(); } catch(_){} });
        chartInstances = [];
    }

    async function render() {
        _destroyCharts();
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();

        if (!prog) {
            main.innerHTML = PGEmptyState.html({ icon: 'reports', title: 'Program Seçilmedi', description: 'Raporları görüntülemek için önce bir program seç.', action: { label: 'Programlara Git', onclick: "App.navigate('programs')" } });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Raporlar' }])}
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <h2 class="pg-view-title">Raporlar — ${esc(prog.name)}</h2>
                    <div style="display:flex;gap:var(--pg-sp-2)">
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.exportXlsx()">Excel</button>
                        <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.exportPdf()">Print</button>
                    </div>
                </div>
            </div>
            <!-- Tab Navigation -->
            <div class="f5-report-tabs" style="display:flex;gap:4px;margin-bottom:16px;border-bottom:2px solid var(--border-primary,#e2e8f0);padding-bottom:0">
                <button class="f5-tab ${activeTab==='health'?'active':''}" onclick="ReportsView.switchTab('health')">🏥 Health</button>
                <button class="f5-tab ${activeTab==='catalog'?'active':''}" onclick="ReportsView.switchTab('catalog')">📚 Report Catalog</button>
                <button class="f5-tab ${activeTab==='saved'?'active':''}" onclick="ReportsView.switchTab('saved')">💾 Saved Reports</button>
            </div>
            <div id="reportContent"><div style="text-align:center;padding:40px;color:#666">Loading...</div></div>`;

        try {
            if (activeTab === 'health') {
                healthData = await API.get(`/reports/program-health/${prog.id}`);
                renderHealth();
            } else if (activeTab === 'catalog') {
                await renderCatalog();
            } else if (activeTab === 'saved') {
                await renderSaved();
            }
        } catch (err) {
            document.getElementById('reportContent').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">⚠️</div>
                    <div class="empty-state__title">Error</div>
                    <p>${esc(err.message || 'Unknown error')}</p>
                </div>`;
        }
    }

    function switchTab(tab) {
        activeTab = tab;
        render();
    }

    // ── Health Tab (original) ───────────────────────────────────────────

    function renderHealth() {
        if (!healthData) return;
        const h = healthData;
        const a = h.areas || {};

        const container = document.getElementById('reportContent');
        container.innerHTML = `
            <div class="card" style="margin-bottom:16px;padding:20px;display:flex;align-items:center;justify-content:space-between">
                <div>
                    <h2 style="margin:0 0 4px">Program Status: ${ragBadge(h.overall_rag)}</h2>
                    <span style="color:#666;font-size:14px">
                        ${h.current_phase ? `Current Phase: <strong>${esc(h.current_phase)}</strong>` : ''}
                        ${h.days_to_go_live != null ? ` · Go-Live in <strong>${h.days_to_go_live}</strong> days` : ''}
                    </span>
                </div>
                <span style="color:#999;font-size:12px">${h.generated_at ? new Date(h.generated_at).toLocaleString() : ''}</span>
            </div>

            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:20px">
                ${renderAreaCard('Explore', a.explore, [
                    {label: 'Workshops', value: `${a.explore?.workshops?.completed || 0}/${a.explore?.workshops?.total || 0}`, pct: a.explore?.workshops?.pct},
                    {label: 'Requirements Approved', pct: a.explore?.requirements?.pct},
                    {label: 'Overdue OIs', value: a.explore?.open_items?.overdue || 0, alert: (a.explore?.open_items?.overdue || 0) > 0},
                ])}
                ${renderAreaCard('Backlog', a.backlog, [
                    {label: 'Items Done', value: `${a.backlog?.items?.done || 0}/${a.backlog?.items?.total || 0}`, pct: a.backlog?.items?.pct},
                ])}
                ${renderAreaCard('Testing', a.testing, [
                    {label: 'Pass Rate', pct: a.testing?.pass_rate},
                    {label: 'Test Cases', value: a.testing?.test_cases || 0},
                    {label: 'Open Defects', value: a.testing?.defects?.open || 0, alert: (a.testing?.defects?.s1_open || 0) > 0},
                    {label: 'S1 Open', value: a.testing?.defects?.s1_open || 0, alert: (a.testing?.defects?.s1_open || 0) > 0},
                ])}
                ${renderAreaCard('RAID', a.raid, [
                    {label: 'Open Risks', value: a.raid?.risks_open || 0},
                    {label: 'Red Risks', value: a.raid?.risks_red || 0, alert: (a.raid?.risks_red || 0) > 0},
                    {label: 'Overdue Actions', value: a.raid?.actions_overdue || 0, alert: (a.raid?.actions_overdue || 0) > 0},
                ])}
                ${renderAreaCard('Integration', a.integration, [
                    {label: 'Interfaces Live', value: `${a.integration?.interfaces?.live || 0}/${a.integration?.interfaces?.total || 0}`, pct: a.integration?.interfaces?.pct},
                ])}
            </div>

            <div class="card" style="padding:16px">
                <h3 style="margin:0 0 12px">Phase Timeline</h3>
                <table class="data-table">
                    <thead><tr>
                        <th>Phase</th><th>Status</th><th>Completion</th>
                        <th>Planned Start</th><th>Planned End</th>
                    </tr></thead>
                    <tbody>
                        ${(h.phases || []).map(p => `
                            <tr>
                                <td><strong>${esc(p.name)}</strong></td>
                                <td>${statusBadge(p.status)}</td>
                                <td>${pctBar(p.completion_pct, RAG_COLORS[p.completion_pct >= 70 ? 'green' : p.completion_pct >= 40 ? 'amber' : 'red'])}</td>
                                <td>${p.planned_start || '—'}</td>
                                <td>${p.planned_end || '—'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    // ── Catalog Tab ─────────────────────────────────────────────────────

    async function renderCatalog() {
        const container = document.getElementById('reportContent');
        try {
            const resp = await API.get('/reports/presets');
            presets = resp.presets || [];
        } catch(_) {
            presets = [];
        }

        const grouped = {};
        CATEGORY_KEYS.forEach(k => { grouped[k] = []; });
        presets.forEach(p => {
            const cat = p.category || 'custom';
            if (!grouped[cat]) grouped[cat] = [];
            grouped[cat].push(p);
        });

        container.innerHTML = `
            <div class="f5-catalog-grid">
                ${CATEGORY_KEYS.map(cat => `
                    <div class="card f5-category-card">
                        <h3 style="margin:0 0 12px;font-size:15px">${CATEGORY_LABELS[cat] || cat}</h3>
                        <div style="display:flex;flex-direction:column;gap:6px">
                            ${(grouped[cat] || []).map(p => `
                                <button class="f5-preset-btn" onclick="ReportsView.runPreset('${p.key}')">
                                    <span class="f5-chart-icon">${chartIcon(p.chart_type)}</span>
                                    <span>${esc(p.name)}</span>
                                </button>
                            `).join('')}
                            ${(grouped[cat] || []).length === 0 ? '<span style="color:#999;font-size:13px">No reports</span>' : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
            <div id="presetResult" style="margin-top:16px"></div>
        `;
    }

    function chartIcon(type) {
        const icons = {
            bar: '📊', line: '📈', pie: '🥧', donut: '🍩', gauge: '⏱️',
            heatmap: '🗺️', kpi: '🔢', table: '📋', treemap: '🌳'
        };
        return icons[type] || '📊';
    }

    async function runPreset(key) {
        const prog = App.getActiveProgram();
        if (!prog) return;
        const resultDiv = document.getElementById('presetResult');
        resultDiv.innerHTML = '<div style="text-align:center;padding:20px;color:#666">Running report...</div>';
        try {
            const data = await API.get(`/reports/presets/${key}/${prog.id}`);
            renderPresetResult(data);
        } catch (err) {
            resultDiv.innerHTML = `<div class="card" style="padding:16px;color:#E74C3C">Error: ${esc(err.message)}</div>`;
        }
    }

    function renderPresetResult(report) {
        const resultDiv = document.getElementById('presetResult');
        _destroyCharts();

        const title = report.title || 'Report Result';
        const chartType = report.chart_type;

        let summaryHtml = '';
        if (report.summary) {
            const s = report.summary;
            if (s.value !== undefined) {
                summaryHtml = `<div class="f5-kpi-card"><span class="f5-kpi-value">${s.value}${s.unit || ''}</span><span class="f5-kpi-label">${s.label || ''}</span></div>`;
            } else {
                summaryHtml = `<div style="font-size:13px;color:#666;margin-bottom:8px">${Object.entries(s).map(([k,v]) => `<strong>${k}:</strong> ${v}`).join(' · ')}</div>`;
            }
        }

        if (chartType === 'table') {
            const columns = report.columns || (report.data && report.data.length ? Object.keys(report.data[0]) : []);
            const rows = report.data || [];
            resultDiv.innerHTML = `
                <div class="card" style="padding:16px">
                    <h3 style="margin:0 0 12px">${esc(title)}</h3>
                    ${summaryHtml}
                    <div style="overflow-x:auto">
                        <table class="data-table">
                            <thead><tr>${columns.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
                            <tbody>${rows.slice(0, 100).map(r => `<tr>${columns.map(c => `<td>${esc(String(r[c] ?? ''))}</td>`).join('')}</tr>`).join('')}</tbody>
                        </table>
                    </div>
                    <span style="font-size:12px;color:#999">${rows.length} rows</span>
                </div>`;
            return;
        }

        if (chartType === 'kpi') {
            resultDiv.innerHTML = `
                <div class="card" style="padding:24px;text-align:center">
                    <h3 style="margin:0 0 16px">${esc(title)}</h3>
                    ${summaryHtml}
                </div>`;
            return;
        }

        // Chart types: bar, line, pie, donut, gauge
        resultDiv.innerHTML = `
            <div class="card" style="padding:16px">
                <h3 style="margin:0 0 12px">${esc(title)}</h3>
                ${summaryHtml}
                <div style="position:relative;height:320px"><canvas id="f5ReportChart"></canvas></div>
            </div>`;

        if (typeof Chart === 'undefined') return;

        const ctx = document.getElementById('f5ReportChart');
        if (!ctx) return;

        const labels = report.labels || [];
        const datasets = (report.datasets || []).map((ds, i) => {
            const colors = ['#0070f3', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
            const base = {
                label: ds.label || `Dataset ${i+1}`,
                data: ds.data || [],
            };
            if (['pie', 'donut'].includes(chartType)) {
                base.backgroundColor = colors;
            } else {
                base.backgroundColor = ds.color || colors[i % colors.length];
                base.borderColor = ds.color || colors[i % colors.length];
                if (chartType === 'line') base.fill = false;
            }
            return base;
        });

        const cjsType = chartType === 'donut' ? 'doughnut' : (chartType === 'gauge' ? 'doughnut' : chartType);
        const opts = { responsive: true, maintainAspectRatio: false };
        if (chartType === 'gauge') {
            opts.circumference = 180;
            opts.rotation = -90;
            opts.cutout = '75%';
        }

        const chart = new Chart(ctx, {
            type: cjsType,
            data: { labels, datasets },
            options: opts,
        });
        chartInstances.push(chart);
    }

    // ── Saved Reports Tab ───────────────────────────────────────────────

    async function renderSaved() {
        const container = document.getElementById('reportContent');
        const prog = App.getActiveProgram();
        try {
            const resp = await API.get(`/reports/definitions?program_id=${prog.id}`);
            const defs = resp.definitions || [];
            if (defs.length === 0) {
                container.innerHTML = PGEmptyState.html({ icon: 'reports', title: 'Kayıtlı Rapor Yok', description: 'Katalogdan bir preset raporu çalıştır ve kaydet.' });
                return;
            }
            container.innerHTML = `
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px">
                    ${defs.map(d => `
                        <div class="card" style="padding:16px">
                            <div style="display:flex;justify-content:space-between;align-items:start">
                                <div>
                                    <h4 style="margin:0 0 4px">${esc(d.name)}</h4>
                                    <span style="font-size:12px;color:#999">${CATEGORY_LABELS[d.category] || d.category} · ${d.chart_type}</span>
                                </div>
                                <div style="display:flex;gap:4px">
                                    <button class="btn btn-sm" onclick="ReportsView.runDefinition(${d.id})" title="Run">▶️</button>
                                    <button class="btn btn-sm btn-danger" onclick="ReportsView.deleteDefinition(${d.id})" title="Delete">🗑️</button>
                                </div>
                            </div>
                            ${d.description ? `<p style="margin:8px 0 0;font-size:13px;color:#666">${esc(d.description)}</p>` : ''}
                        </div>
                    `).join('')}
                </div>
                <div id="presetResult" style="margin-top:16px"></div>`;
        } catch (err) {
            container.innerHTML = `<div class="card" style="padding:16px;color:#E74C3C">Error: ${esc(err.message)}</div>`;
        }
    }

    async function runDefinition(id) {
        const resultDiv = document.getElementById('presetResult');
        if (!resultDiv) return;
        resultDiv.innerHTML = '<div style="text-align:center;padding:20px;color:#666">Running...</div>';
        try {
            const data = await API.get(`/reports/definitions/${id}/run`);
            renderPresetResult(data);
        } catch (err) {
            resultDiv.innerHTML = `<div class="card" style="padding:16px;color:#E74C3C">Error: ${esc(err.message)}</div>`;
        }
    }

    async function deleteDefinition(id) {
        if (!confirm('Delete this saved report?')) return;
        try {
            await API.delete(`/reports/definitions/${id}`);
            renderSaved();
        } catch (err) {
            alert('Error: ' + (err.message || 'Unknown'));
        }
    }

    function renderAreaCard(title, area, metrics) {
        if (!area) return '';
        const rag = area.rag || '—';
        return `
            <div class="card" style="padding:16px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <h3 style="margin:0">${title}</h3>
                    ${ragBadge(rag)}
                </div>
                <div style="display:flex;flex-direction:column;gap:6px">
                    ${metrics.map(m => `
                        <div style="display:flex;justify-content:space-between;align-items:center;font-size:14px">
                            <span style="color:#666">${m.label}</span>
                            <span style="${m.alert ? 'color:#E74C3C;font-weight:600' : ''}">
                                ${m.pct != null ? pctBar(m.pct, RAG_COLORS[m.pct >= 70 ? 'green' : m.pct >= 40 ? 'amber' : 'red']) : (m.value ?? '—')}
                            </span>
                        </div>
                    `).join('')}
                </div>
            </div>`;
    }

    function statusBadge(status) {
        return PGStatusRegistry.badge(status);
    }

    function exportXlsx() {
        const prog = App.getActiveProgram();
        if (!prog) return;
        window.open(`/api/v1/reports/export/xlsx/${prog.id}`, '_blank');
    }

    function exportPdf() {
        const prog = App.getActiveProgram();
        if (!prog) return;
        window.open(`/api/v1/reports/export/pdf/${prog.id}`, '_blank');
    }

    return { render, switchTab, runPreset, runDefinition, deleteDefinition, exportXlsx, exportPdf };
})();
