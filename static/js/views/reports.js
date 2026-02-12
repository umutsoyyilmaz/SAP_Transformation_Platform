const ReportsView = (() => {
    let healthData = null;

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    const RAG_COLORS = { green: '#27AE60', amber: '#F39C12', red: '#E74C3C' };
    const RAG_LABELS = { green: 'On Track', amber: 'At Risk', red: 'Critical' };

    function ragBadge(rag) {
        const color = RAG_COLORS[rag] || '#999';
        const label = RAG_LABELS[rag] || rag || '—';
        return `<span style="display:inline-block;padding:4px 12px;background:${color};color:#fff;border-radius:4px;font-weight:600;font-size:13px">${label}</span>`;
    }

    function pctBar(pct, color) {
        return `<div style="background:#e9ecef;border-radius:4px;height:8px;width:120px;display:inline-block;vertical-align:middle;margin-left:8px">
            <div style="background:${color || '#0070f3'};height:100%;width:${Math.min(pct, 100)}%;border-radius:4px"></div>
        </div> <span style="font-size:13px;color:#666">${pct}%</span>`;
    }

    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();

        if (!prog) {
            main.innerHTML = `
                <div class="page-header"><h1>Reports</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">📊</div>
                    <div class="empty-state__title">No Program Selected</div>
                    <p>Select a program to view reports.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>Reports — ${esc(prog.name)}</h1>
                <div>
                    <button class="btn btn-secondary" onclick="ReportsView.exportXlsx()">📥 Excel</button>
                    <button class="btn btn-secondary" onclick="ReportsView.exportPdf()">📄 Print Report</button>
                </div>
            </div>
            <div id="reportContent"><div style="text-align:center;padding:40px;color:#666">Loading report data...</div></div>`;

        try {
            healthData = await API.get(`/reports/program-health/${prog.id}`);
            renderHealth();
        } catch (err) {
            document.getElementById('reportContent').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">⚠️</div>
                    <div class="empty-state__title">Error Loading Report</div>
                    <p>${esc(err.message || 'Unknown error')}</p>
                </div>`;
        }
    }

    function renderHealth() {
        if (!healthData) return;
        const h = healthData;
        const a = h.areas || {};

        const container = document.getElementById('reportContent');
        container.innerHTML = `
            <!-- Overall Status Banner -->
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

            <!-- Area Health Cards -->
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

            <!-- Phase Timeline -->
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
        const colors = {
            active: '#0070f3', completed: '#27AE60', planned: '#a9b4be',
            not_started: '#a9b4be', on_hold: '#F39C12',
        };
        const c = colors[status] || '#a9b4be';
        return `<span style="display:inline-block;padding:2px 8px;background:${c}22;color:${c};border-radius:4px;font-size:12px;font-weight:600">${status || '—'}</span>`;
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

    return { render, exportXlsx, exportPdf };
})();
