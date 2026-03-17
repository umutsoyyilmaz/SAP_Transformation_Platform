/**
 * SAP Transformation Platform — WR-3.5
 * Traceability View Component
 *
 * Displays a visual chain graph for a requirement:
 *   Requirement → Backlog/Config → Test Case → Defect
 *   (+ linked Open Items)
 *
 * API: GET /api/v1/trace/requirement/<id>
 *
 * Usage:
 *   TraceView.showForRequirement(reqId);  // opens modal with trace
 *   TraceView.renderInline(reqId);        // returns HTML promise
 */
const TraceView = (() => {
    'use strict';

    const esc = (s) => {
        const d = document.createElement('div');
        d.textContent = s ?? '';
        return d.innerHTML;
    };

    // ── Entity type config ──────────────────────────────────────────
    const ENTITY_STYLES = {
        requirement:  { icon: '📝', color: '#0070f2', label: 'Requirement' },
        backlog_item: { icon: '⚙️', color: '#7c3aed', label: 'WRICEF Item' },
        config_item:  { icon: '🔧', color: '#6366f1', label: 'Config Item' },
        test_case:    { icon: '🧪', color: '#059669', label: 'Test Case' },
        defect:       { icon: '🐛', color: '#dc2626', label: 'Defect' },
        open_item:    { icon: '📌', color: '#d97706', label: 'Open Item' },
    };

    // ── Fetch trace data ────────────────────────────────────────────
    async function fetchTrace(reqId) {
        return API.get(`/trace/requirement/${reqId}`);
    }

    // ── Show in Modal ───────────────────────────────────────────────
    async function showForRequirement(reqId) {
        App.openModal(`
            <div style="min-width:600px;max-width:900px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <h2 style="margin:0;font-size:18px">Traceability Chain</h2>
                    <button class="btn btn-sm" onclick="App.closeModal()" style="color:var(--sap-text-secondary)">✕ Close</button>
                </div>
                <div id="traceViewContent" style="text-align:center;padding:30px;color:var(--sap-text-secondary)">
                    <div style="font-size:24px;margin-bottom:8px">⏳</div>
                    Loading trace data…
                </div>
            </div>
        `);

        try {
            const data = await fetchTrace(reqId);
            const container = document.getElementById('traceViewContent');
            if (!container) return;
            container.innerHTML = renderTraceGraph(data);
        } catch (err) {
            const container = document.getElementById('traceViewContent');
            if (container) {
                container.innerHTML = `<div style="color:var(--sap-negative)">Error loading trace: ${esc(err.message || 'Unknown error')}</div>`;
            }
        }
    }

    // ── Render inline (returns HTML string, async) ──────────────────
    async function renderInline(reqId) {
        try {
            const data = await fetchTrace(reqId);
            return renderTraceGraph(data);
        } catch (err) {
            return `<div style="color:var(--sap-negative);padding:12px">Error: ${esc(err.message)}</div>`;
        }
    }

    // ── Graph rendering ─────────────────────────────────────────────
    function renderTraceGraph(data) {
        const req = data.requirement;
        if (!req) return '<div>No requirement data</div>';

        const cov = data.coverage || {};
        const depth = data.chain_depth || 0;

        // Coverage summary strip
        const coverageHTML = `
            <div class="trace-coverage">
                ${_covBadge('WRICEF', cov.backlog || 0, 'backlog_item')}
                ${_covBadge('Config', cov.config || 0, 'config_item')}
                ${_covBadge('Tests', cov.test || 0, 'test_case')}
                ${_covBadge('Defects', cov.defect || 0, 'defect')}
                ${_covBadge('Open Items', cov.open_item || 0, 'open_item')}
                <span class="trace-depth">Depth: ${depth}/4</span>
            </div>`;

        // Chain visualization
        const layers = [];

        // Layer 1: Requirement
        layers.push(_renderLayer([{
            type: 'requirement',
            id: req.id,
            title: req.title,
            code: req.code,
            status: req.status,
            extra: req.priority ? `Priority: ${req.priority}` : '',
        }]));

        // Layer 2: Backlog + Config items
        const layer2 = [];
        (data.backlog_items || []).forEach(b => {
            layer2.push({
                type: 'backlog_item', id: b.id, title: b.title,
                code: b.code, status: b.status, extra: b.type || '',
            });
        });
        (data.config_items || []).forEach(c => {
            layer2.push({
                type: 'config_item', id: c.id, title: c.title,
                code: c.code, status: c.status,
            });
        });
        if (layer2.length) {
            layers.push(_renderConnector());
            layers.push(_renderLayer(layer2));
        }

        // Layer 3: Test cases
        const layer3 = (data.test_cases || []).map(tc => ({
            type: 'test_case', id: tc.id, title: tc.title,
            code: tc.code, status: tc.status, extra: tc.result || '',
        }));
        if (layer3.length) {
            layers.push(_renderConnector());
            layers.push(_renderLayer(layer3));
        }

        // Layer 4: Defects
        const layer4 = (data.defects || []).map(d => ({
            type: 'defect', id: d.id, title: d.title,
            code: d.code, status: d.status, extra: d.severity || '',
        }));
        if (layer4.length) {
            layers.push(_renderConnector());
            layers.push(_renderLayer(layer4));
        }

        // Separate: Open items (linked via M:N)
        const oiList = (data.open_items || []).map(oi => ({
            type: 'open_item', id: oi.id, title: oi.title,
            code: oi.code, status: oi.status, extra: oi.priority || '',
        }));
        let oiHTML = '';
        if (oiList.length) {
            oiHTML = `
                <div class="trace-separator">
                    <span>Linked Open Items</span>
                </div>
                ${_renderLayer(oiList)}`;
        }

        return `
            <div class="trace-graph">
                ${coverageHTML}
                <div class="trace-chain">${layers.join('')}</div>
                ${oiHTML}
            </div>`;
    }

    // ── Helpers ──────────────────────────────────────────────────────
    function _covBadge(label, count, type) {
        const style = ENTITY_STYLES[type] || {};
        const color = count > 0 ? style.color : '#999';
        return `<span class="trace-cov-badge" style="border-color:${color}">
            <span style="color:${color};font-weight:600">${count}</span>
            <span>${label}</span>
        </span>`;
    }

    function _renderConnector() {
        return `<div class="trace-connector">
            <div class="trace-connector__line"></div>
            <span class="trace-connector__arrow">▼</span>
        </div>`;
    }

    function _renderLayer(entities) {
        const cards = entities.map(e => {
            const style = ENTITY_STYLES[e.type] || {};
            const statusCls = _statusClass(e.status);
            return `
                <div class="trace-node" style="border-color:${style.color}">
                    <div class="trace-node__header" style="background:${style.color}10">
                        <span class="trace-node__icon">${style.icon}</span>
                        <span class="trace-node__type">${style.label}</span>
                        <span class="trace-node__code">${esc(e.code || '')}</span>
                    </div>
                    <div class="trace-node__body">
                        <div class="trace-node__title">${esc(e.title || 'Untitled')}</div>
                        <div class="trace-node__meta">
                            <span class="trace-status ${statusCls}">${esc(e.status || '—')}</span>
                            ${e.extra ? `<span class="trace-node__extra">${esc(e.extra)}</span>` : ''}
                        </div>
                    </div>
                </div>`;
        }).join('');
        return `<div class="trace-layer">${cards}</div>`;
    }

    function _statusClass(status) {
        if (!status) return '';
        const s = status.toLowerCase();
        if (['approved', 'pass', 'closed', 'done', 'verified', 'resolved', 'completed'].includes(s)) return 'trace-status--green';
        if (['in_progress', 'in_backlog', 'retest', 'assigned', 'in_review'].includes(s)) return 'trace-status--amber';
        if (['rejected', 'fail', 'blocked', 'reopened', 'deferred'].includes(s)) return 'trace-status--red';
        return '';
    }

    return { showForRequirement, renderInline, fetchTrace, renderTraceGraph };
})();
