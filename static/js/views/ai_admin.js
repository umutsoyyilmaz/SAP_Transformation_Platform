/**
 * SAP Transformation Platform — AI Admin Dashboard (Sprint 7)
 *
 * AI usage stats, cost monitoring, suggestion overview, embedding stats.
 */
const AIAdminView = (() => {
    let _charts = {};

    async function render() {
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="pg-view-header">
                <h1>🤖 AI Admin Dashboard</h1>
                <p class="text-muted">AI infrastructure monitoring — usage, cost, suggestions & embeddings</p>
            </div>

            <!-- KPI Cards -->
            <div class="kpi-row" id="aiKpiCards">
                <div class="kpi-card"><div class="kpi-card__value">—</div><div class="kpi-card__label">Total API Calls</div></div>
                <div class="kpi-card"><div class="kpi-card__value">—</div><div class="kpi-card__label">Total Tokens</div></div>
                <div class="kpi-card"><div class="kpi-card__value">—</div><div class="kpi-card__label">Total Cost (USD)</div></div>
                <div class="kpi-card"><div class="kpi-card__value">—</div><div class="kpi-card__label">Avg Latency (ms)</div></div>
                <div class="kpi-card"><div class="kpi-card__value">—</div><div class="kpi-card__label">Error Rate</div></div>
                <div class="kpi-card"><div class="kpi-card__value">—</div><div class="kpi-card__label">Pending Suggestions</div></div>
            </div>

            <!-- Charts Row -->
            <div class="chart-row" style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px;">
                <div class="card">
                    <h3>Cost by Provider</h3>
                    <div style="height:250px"><canvas id="aiCostChart"></canvas></div>
                </div>
                <div class="card">
                    <h3>Suggestions by Status</h3>
                    <div style="height:250px"><canvas id="aiSuggestionChart"></canvas></div>
                </div>
            </div>

            <!-- Tabs: Suggestions | Usage Log | Audit Log | Embeddings | Prompts -->
            <div class="tabs" style="margin-top:24px">
                <button class="tab active" onclick="AIAdminView.switchTab('suggestions')">💡 Suggestions</button>
                <button class="tab" onclick="AIAdminView.switchTab('usage')">📊 Usage Log</button>
                <button class="tab" onclick="AIAdminView.switchTab('audit')">📋 Audit Log</button>
                <button class="tab" onclick="AIAdminView.switchTab('embeddings')">🔍 Embeddings</button>
                <button class="tab" onclick="AIAdminView.switchTab('prompts')">📝 Prompts</button>
            </div>
            <div id="aiTabContent" style="margin-top:16px"></div>
        `;

        await loadDashboard();
        switchTab('suggestions');
    }

    async function loadDashboard() {
        try {
            const data = await API.get('/ai/admin/dashboard');
            renderKPIs(data);
            renderCharts(data);
        } catch (e) {
            console.warn('AI Dashboard load failed:', e);
            // Show empty state — AI module may not have data yet
            const cards = document.querySelectorAll('#aiKpiCards .kpi-card__value');
            cards.forEach(c => { c.textContent = '0'; });
        }
    }

    function renderKPIs(data) {
        const u = data.usage || {};
        const s = data.suggestions || {};
        const cards = document.querySelectorAll('#aiKpiCards .kpi-card__value');
        if (cards.length >= 6) {
            cards[0].textContent = (u.total_calls || 0).toLocaleString();
            cards[1].textContent = (u.total_tokens || 0).toLocaleString();
            cards[2].textContent = '$' + (u.total_cost_usd || 0).toFixed(4);
            cards[3].textContent = (u.avg_latency_ms || 0) + 'ms';
            cards[4].textContent = (u.error_rate || 0).toFixed(1) + '%';
            cards[5].textContent = (s.by_status || {}).pending || 0;
        }
    }

    function renderCharts(data) {
        // Destroy old charts
        Object.values(_charts).forEach(c => c.destroy && c.destroy());
        _charts = {};

        // Cost by provider
        const providers = data.usage?.by_provider || {};
        const providerNames = Object.keys(providers);
        const providerCosts = providerNames.map(p => providers[p].cost || 0);

        const costCtx = document.getElementById('aiCostChart');
        if (costCtx && providerNames.length > 0) {
            _charts.cost = new Chart(costCtx, {
                type: 'doughnut',
                data: {
                    labels: providerNames,
                    datasets: [{
                        data: providerCosts,
                        backgroundColor: ['#0070f2', '#e76500', '#107e3e', '#bb0000'],
                    }],
                },
                options: { responsive: true, maintainAspectRatio: false },
            });
        }

        // Suggestions by status
        const statuses = data.suggestions?.by_status || {};
        const statusNames = Object.keys(statuses);
        const statusCounts = statusNames.map(s => statuses[s]);
        const statusColors = {
            pending: '#e76500', approved: '#107e3e', rejected: '#bb0000',
            modified: '#0070f2', applied: '#1a9898', expired: '#999',
        };

        const sugCtx = document.getElementById('aiSuggestionChart');
        if (sugCtx && statusNames.length > 0) {
            _charts.suggestions = new Chart(sugCtx, {
                type: 'doughnut',
                data: {
                    labels: statusNames,
                    datasets: [{
                        data: statusCounts,
                        backgroundColor: statusNames.map(s => statusColors[s] || '#999'),
                    }],
                },
                options: { responsive: true, maintainAspectRatio: false },
            });
        }
    }

    // ── Tab Navigation ───────────────────────────────────────────────────

    function switchTab(tab) {
        document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
        event?.target?.classList?.add('active') ||
            document.querySelector(`.tabs .tab[onclick*="${tab}"]`)?.classList.add('active');

        const loaders = {
            suggestions: loadSuggestions,
            usage: loadUsageLog,
            audit: loadAuditLog,
            embeddings: loadEmbeddings,
            prompts: loadPrompts,
        };
        (loaders[tab] || loaders.suggestions)();
    }

    // ── Suggestions Tab ──────────────────────────────────────────────────

    async function loadSuggestions() {
        const container = document.getElementById('aiTabContent');
        container.innerHTML = '<p class="text-muted">Loading suggestions...</p>';
        try {
            const data = await API.get('/ai/suggestions?per_page=50');
            if (!data.items || data.items.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state__icon">💡</div>
                        <div class="empty-state__title">No AI Suggestions Yet</div>
                        <p>Suggestions will appear here when AI assistants analyze your data.</p>
                    </div>`;
                return;
            }
            container.innerHTML = `
                <table class="data-table">
                    <thead><tr>
                        <th>ID</th><th>Type</th><th>Entity</th><th>Title</th>
                        <th>Confidence</th><th>Status</th><th>Created</th><th>Actions</th>
                    </tr></thead>
                    <tbody>
                        ${data.items.map(s => `
                            <tr>
                                <td>${s.id}</td>
                                <td><span class="badge">${s.suggestion_type}</span></td>
                                <td>${s.entity_type}/${s.entity_id}</td>
                                <td>${s.title}</td>
                                <td>${(s.confidence * 100).toFixed(0)}%</td>
                                <td><span class="badge badge-${s.status}">${s.status}</span></td>
                                <td>${s.created_at ? new Date(s.created_at).toLocaleDateString() : ''}</td>
                                <td>
                                    ${s.status === 'pending' ? `
                                        <button class="btn btn-sm btn-primary" onclick="AIAdminView.approveSuggestion(${s.id})">✓</button>
                                        <button class="btn btn-sm btn-danger" onclick="AIAdminView.rejectSuggestion(${s.id})">✗</button>
                                    ` : '—'}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <p class="text-muted" style="margin-top:8px">Total: ${data.total} suggestions</p>`;
        } catch (e) {
            container.innerHTML = '<p class="text-muted">No suggestions data available.</p>';
        }
    }

    async function approveSuggestion(id) {
        try {
            await API.patch(`/ai/suggestions/${id}/approve`, { reviewer: 'admin' });
            App.toast('Suggestion approved', 'success');
            loadSuggestions();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function rejectSuggestion(id) {
        try {
            await API.patch(`/ai/suggestions/${id}/reject`, { reviewer: 'admin' });
            App.toast('Suggestion rejected', 'info');
            loadSuggestions();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    // ── Usage Log Tab ────────────────────────────────────────────────────

    async function loadUsageLog() {
        const container = document.getElementById('aiTabContent');
        container.innerHTML = '<p class="text-muted">Loading usage data...</p>';
        try {
            const data = await API.get('/ai/usage?days=30');
            container.innerHTML = `
                <div class="kpi-row" style="margin-bottom:16px">
                    <div class="kpi-card"><div class="kpi-card__value">${data.total_calls}</div><div class="kpi-card__label">Calls (30d)</div></div>
                    <div class="kpi-card"><div class="kpi-card__value">${data.total_tokens?.toLocaleString()}</div><div class="kpi-card__label">Tokens</div></div>
                    <div class="kpi-card"><div class="kpi-card__value">$${data.total_cost_usd}</div><div class="kpi-card__label">Cost</div></div>
                    <div class="kpi-card"><div class="kpi-card__value">${data.avg_latency_ms}ms</div><div class="kpi-card__label">Avg Latency</div></div>
                </div>
                <h4>By Model</h4>
                <table class="data-table">
                    <thead><tr><th>Model</th><th>Calls</th><th>Tokens</th><th>Cost (USD)</th></tr></thead>
                    <tbody>
                        ${Object.entries(data.by_model || {}).map(([m, v]) =>
                            `<tr><td>${m}</td><td>${v.calls}</td><td>${v.tokens?.toLocaleString()}</td><td>$${v.cost}</td></tr>`
                        ).join('')}
                    </tbody>
                </table>
                <h4 style="margin-top:16px">By Purpose</h4>
                <table class="data-table">
                    <thead><tr><th>Purpose</th><th>Calls</th><th>Tokens</th><th>Cost (USD)</th></tr></thead>
                    <tbody>
                        ${Object.entries(data.by_purpose || {}).map(([p, v]) =>
                            `<tr><td>${p}</td><td>${v.calls}</td><td>${v.tokens?.toLocaleString()}</td><td>$${v.cost}</td></tr>`
                        ).join('')}
                    </tbody>
                </table>`;
        } catch (e) {
            container.innerHTML = '<p class="text-muted">No usage data available yet.</p>';
        }
    }

    // ── Audit Log Tab ────────────────────────────────────────────────────

    async function loadAuditLog() {
        const container = document.getElementById('aiTabContent');
        container.innerHTML = '<p class="text-muted">Loading audit log...</p>';
        try {
            const data = await API.get('/ai/audit-log?per_page=50');
            if (!data.items || data.items.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="empty-state__icon">📋</div><div class="empty-state__title">No Audit Entries</div><p>AI operation logs will appear here.</p></div>';
                return;
            }
            container.innerHTML = `
                <table class="data-table">
                    <thead><tr><th>Time</th><th>Action</th><th>Provider</th><th>Model</th><th>Tokens</th><th>Cost</th><th>Latency</th><th>Status</th></tr></thead>
                    <tbody>
                        ${data.items.map(a => `
                            <tr>
                                <td>${a.created_at ? new Date(a.created_at).toLocaleString() : ''}</td>
                                <td><span class="badge">${a.action}</span></td>
                                <td>${a.provider}</td>
                                <td>${a.model}</td>
                                <td>${a.tokens_used}</td>
                                <td>$${a.cost_usd}</td>
                                <td>${a.latency_ms}ms</td>
                                <td>${a.success ? '✅' : '❌'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <p class="text-muted" style="margin-top:8px">Total: ${data.total} entries</p>`;
        } catch (e) {
            container.innerHTML = '<p class="text-muted">No audit data available yet.</p>';
        }
    }

    // ── Embeddings Tab ───────────────────────────────────────────────────

    async function loadEmbeddings() {
        const container = document.getElementById('aiTabContent');
        container.innerHTML = '<p class="text-muted">Loading embedding stats...</p>';
        try {
            const stats = await API.get('/ai/embeddings/stats');
            container.innerHTML = `
                <div class="kpi-row" style="margin-bottom:16px">
                    <div class="kpi-card"><div class="kpi-card__value">${stats.total_chunks}</div><div class="kpi-card__label">Total Chunks</div></div>
                    <div class="kpi-card"><div class="kpi-card__value">${stats.with_embeddings}</div><div class="kpi-card__label">With Vectors</div></div>
                    <div class="kpi-card"><div class="kpi-card__value">${stats.without_embeddings}</div><div class="kpi-card__label">Without Vectors</div></div>
                </div>
                <h4>Chunks by Entity Type</h4>
                <table class="data-table">
                    <thead><tr><th>Entity Type</th><th>Chunk Count</th></tr></thead>
                    <tbody>
                        ${Object.entries(stats.by_entity_type || {}).map(([t, c]) =>
                            `<tr><td>${t}</td><td>${c}</td></tr>`
                        ).join('') || '<tr><td colspan="2">No embeddings indexed yet</td></tr>'}
                    </tbody>
                </table>

                <!-- Search test -->
                <div class="card" style="margin-top:20px;padding:16px">
                    <h4>🔍 Test Semantic Search</h4>
                    <div class="form-row" style="align-items:end">
                        <div class="form-group" style="flex:1">
                            <input id="aiSearchQuery" class="form-control" placeholder="Enter search query...">
                        </div>
                        <div class="form-group">
                            <button class="btn btn-primary" onclick="AIAdminView.testSearch()">Search</button>
                        </div>
                    </div>
                    <div id="aiSearchResults"></div>
                </div>`;
        } catch (e) {
            container.innerHTML = '<p class="text-muted">No embedding data available yet.</p>';
        }
    }

    async function testSearch() {
        const query = document.getElementById('aiSearchQuery')?.value;
        if (!query) return;
        const results = document.getElementById('aiSearchResults');
        results.innerHTML = '<p class="text-muted">Searching...</p>';
        try {
            const data = await API.post('/ai/embeddings/search', { query, top_k: 5 });
            if (data.results.length === 0) {
                results.innerHTML = '<p class="text-muted">No results found.</p>';
                return;
            }
            results.innerHTML = `
                <table class="data-table" style="margin-top:8px">
                    <thead><tr><th>Score</th><th>Entity</th><th>Module</th><th>Text (preview)</th></tr></thead>
                    <tbody>
                        ${data.results.map(r => `
                            <tr>
                                <td><strong>${(r.score * 100).toFixed(1)}%</strong></td>
                                <td>${r.entity_type}/${r.entity_id}</td>
                                <td>${r.module || '—'}</td>
                                <td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.chunk_text.substring(0, 150)}...</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>`;
        } catch (e) {
            results.innerHTML = `<p class="text-muted">Search error: ${e.message}</p>`;
        }
    }

    // ── Prompts Tab ──────────────────────────────────────────────────────

    async function loadPrompts() {
        const container = document.getElementById('aiTabContent');
        container.innerHTML = '<p class="text-muted">Loading prompts...</p>';
        try {
            const data = await API.get('/ai/prompts');
            container.innerHTML = `
                <table class="data-table">
                    <thead><tr><th>Name</th><th>Version</th><th>Description</th><th>A/B Test</th><th>System Preview</th></tr></thead>
                    <tbody>
                        ${(data.prompts || []).map(p => `
                            <tr>
                                <td><strong>${p.name}</strong></td>
                                <td><span class="badge">${p.version}</span></td>
                                <td>${p.description}</td>
                                <td>${p.ab_test ? '✅' : '—'}</td>
                                <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;color:#666">${p.system_preview}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>`;
        } catch (e) {
            container.innerHTML = '<p class="text-muted">No prompt data available.</p>';
        }
    }

    // ── Public API ───────────────────────────────────────────────────────
    return {
        render,
        switchTab,
        approveSuggestion,
        rejectSuggestion,
        testSearch,
    };
})();
