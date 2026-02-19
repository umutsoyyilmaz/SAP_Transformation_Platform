/**
 * SAP Transformation Platform — F4
 * AI Insights View — Smart Search (⌘K), Flaky Tests, Predictive Coverage,
 *                     Suite Optimizer, TC Maintenance.
 *
 * Vanilla JS IIFE pattern matching project conventions.
 */

const AIInsightsView = (() => {
    let programId = null;
    let _activeTab = 'smart-search';

    // ── Render ───────────────────────────────────────────────────────────
    function render() {
        const prog = App.getActiveProgram();
        programId = prog ? prog.id : null;

        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <h1>🧠 AI Insights</h1>
                <p class="page-header__sub">Smart search, flaky-test detection, predictive coverage, suite optimisation & maintenance.</p>
            </div>

            <!-- Tab Bar -->
            <div class="tm-tab-bar ai-insights-tabs">
                <button class="tm-tab-bar__tab active" data-tab="smart-search" onclick="AIInsightsView.switchTab('smart-search')">🔍 Smart Search</button>
                <button class="tm-tab-bar__tab" data-tab="flaky-tests" onclick="AIInsightsView.switchTab('flaky-tests')">⚡ Flaky Tests</button>
                <button class="tm-tab-bar__tab" data-tab="predictive-coverage" onclick="AIInsightsView.switchTab('predictive-coverage')">🎯 Risk Heatmap</button>
                <button class="tm-tab-bar__tab" data-tab="tc-maintenance" onclick="AIInsightsView.switchTab('tc-maintenance')">🔧 TC Maintenance</button>
            </div>

            <div id="aiInsightsContent" class="ai-insights-content"></div>
        `;

        _renderActiveTab();
    }

    function switchTab(tab) {
        _activeTab = tab;
        document.querySelectorAll('.ai-insights-tabs .tm-tab-bar__tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        _renderActiveTab();
    }

    function _renderActiveTab() {
        const container = document.getElementById('aiInsightsContent');
        if (!container) return;
        switch (_activeTab) {
            case 'smart-search':   _renderSmartSearch(container); break;
            case 'flaky-tests':    _renderFlakyTests(container); break;
            case 'predictive-coverage': _renderPredictiveCoverage(container); break;
            case 'tc-maintenance': _renderTCMaintenance(container); break;
        }
    }

    // ── Smart Search ─────────────────────────────────────────────────────
    function _renderSmartSearch(container) {
        container.innerHTML = `
            <div class="card" style="margin-top:var(--space-4)">
                <div class="card-header"><h2>🔍 Natural Language Smart Search</h2></div>
                <div class="card-body">
                    <div class="ai-insights-search-bar">
                        <input type="text" id="aiSmartSearchInput" class="tm-input"
                            placeholder="e.g. 'FI modülünde başarısız olan P1 test case'leri'" 
                            style="flex:1" />
                        <button class="btn btn-primary" onclick="AIInsightsView.runSmartSearch()">Search</button>
                    </div>
                    <p class="text-muted" style="margin-top:var(--space-2);font-size:0.85rem">
                        Tip: Use <kbd>⌘K</kbd> / <kbd>Ctrl+K</kbd> to open smart search from anywhere.
                    </p>
                    <div id="aiSmartSearchResults" style="margin-top:var(--space-4)"></div>
                </div>
            </div>
        `;
        // Focus input
        setTimeout(() => document.getElementById('aiSmartSearchInput')?.focus(), 100);
    }

    async function runSmartSearch() {
        const input = document.getElementById('aiSmartSearchInput');
        const query = (input?.value || '').trim();
        if (!query) return;

        const results = document.getElementById('aiSmartSearchResults');
        results.innerHTML = '<div class="spinner"></div>';

        try {
            const resp = await fetch('/api/v1/ai/smart-search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, program_id: programId }),
            });
            const data = await resp.json();

            if (data.error) {
                results.innerHTML = `<div class="alert alert-warning">${data.error}</div>`;
                return;
            }

            let html = '';
            const items = data.results || [];
            if (items.length) {
                html += `<h3 style="margin-top:var(--space-4)">Results (${items.length})</h3>`;
                html += '<table class="table"><thead><tr>';
                const cols = Object.keys(items[0]).slice(0, 8);
                cols.forEach(c => html += `<th>${c}</th>`);
                html += '</tr></thead><tbody>';
                items.forEach(item => {
                    html += '<tr>';
                    cols.forEach(c => html += `<td>${item[c] ?? ''}</td>`);
                    html += '</tr>';
                });
                html += '</tbody></table>';
            }

            if (!html) html = '<div class="alert alert-info">No results found.</div>';
            results.innerHTML = html;
        } catch (err) {
            results.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
        }
    }

    // ── Flaky Tests ──────────────────────────────────────────────────────
    function _renderFlakyTests(container) {
        container.innerHTML = `
            <div class="card" style="margin-top:var(--space-4)">
                <div class="card-header">
                    <h2>⚡ Flaky Test Detector</h2>
                    <button class="btn btn-primary btn-sm" onclick="AIInsightsView.runFlakyDetection()">Analyze</button>
                </div>
                <div class="card-body" id="flakyTestsResult">
                    <p class="text-muted">Click <strong>Analyze</strong> to detect flaky tests via execution oscillation analysis.</p>
                </div>
            </div>
        `;
    }

    async function runFlakyDetection() {
        const container = document.getElementById('flakyTestsResult');
        container.innerHTML = '<div class="spinner"></div>';

        try {
            const resp = await fetch(`/api/v1/ai/programs/${programId}/flaky-tests`);
            const data = await resp.json();

            if (data.error) {
                container.innerHTML = `<div class="alert alert-warning">${data.error}</div>`;
                return;
            }

            const flaky = data.flaky_tests || [];
            let html = `
                <div class="ai-insights-summary-cards">
                    <div class="ai-insights-stat"><span class="ai-insights-stat__value">${data.total_analyzed || 0}</span><span class="ai-insights-stat__label">Total Analyzed</span></div>
                    <div class="ai-insights-stat ai-insights-stat--warning"><span class="ai-insights-stat__value">${data.flaky_count || 0}</span><span class="ai-insights-stat__label">Flaky Tests</span></div>
                </div>
            `;

            if (flaky.length) {
                html += '<table class="table" style="margin-top:var(--space-4)"><thead><tr><th>Code</th><th>Title</th><th>Flakiness</th><th>Env Correlation</th><th>Recommendation</th></tr></thead><tbody>';
                flaky.forEach(f => {
                    const badge = f.flakiness_score >= 70 ? 'danger' : f.flakiness_score >= 40 ? 'warning' : 'info';
                    html += `<tr>
                        <td><strong>${f.code || ''}</strong></td>
                        <td>${f.title || ''}</td>
                        <td><span class="badge badge--${badge}">${f.flakiness_score}%</span></td>
                        <td>${f.environment_correlation || '—'}</td>
                        <td>${f.recommendation || ''}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
            } else {
                html += '<div class="alert alert-success" style="margin-top:var(--space-4)">No flaky tests detected! ✓</div>';
            }

            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
        }
    }

    // ── Predictive Coverage / Risk Heatmap ──────────────────────────────
    function _renderPredictiveCoverage(container) {
        container.innerHTML = `
            <div class="card" style="margin-top:var(--space-4)">
                <div class="card-header">
                    <h2>🎯 AI Risk Heatmap</h2>
                    <button class="btn btn-primary btn-sm" onclick="AIInsightsView.runPredictiveCoverage()">Generate</button>
                </div>
                <div class="card-body" id="predictiveCoverageResult">
                    <p class="text-muted">Generate a risk heat-map based on defect density, change frequency, and execution gaps.</p>
                </div>
            </div>
        `;
    }

    async function runPredictiveCoverage() {
        const container = document.getElementById('predictiveCoverageResult');
        container.innerHTML = '<div class="spinner"></div>';

        try {
            const resp = await fetch(`/api/v1/ai/programs/${programId}/predictive-coverage`);
            const data = await resp.json();

            if (data.error) {
                container.innerHTML = `<div class="alert alert-warning">${data.error}</div>`;
                return;
            }

            const heatMap = data.heat_map || [];
            const summary = data.summary || {};

            let html = `
                <div class="ai-insights-summary-cards">
                    <div class="ai-insights-stat"><span class="ai-insights-stat__value">${summary.total_areas || 0}</span><span class="ai-insights-stat__label">Risk Areas</span></div>
                    <div class="ai-insights-stat ai-insights-stat--danger"><span class="ai-insights-stat__value">${summary.high_risk_count || 0}</span><span class="ai-insights-stat__label">High Risk</span></div>
                    <div class="ai-insights-stat ai-insights-stat--warning"><span class="ai-insights-stat__value">${(data.never_executed || []).length}</span><span class="ai-insights-stat__label">Never Executed</span></div>
                    <div class="ai-insights-stat ai-insights-stat--info"><span class="ai-insights-stat__value">${(data.stale_executed || []).length}</span><span class="ai-insights-stat__label">Stale</span></div>
                </div>
            `;

            if (heatMap.length) {
                html += '<h3 style="margin-top:var(--space-4)">Risk Heatmap</h3>';
                html += '<div class="ai-risk-heatmap">';
                const maxRisk = heatMap[0]?.risk_score || 1;
                heatMap.forEach(cell => {
                    const pct = Math.round((cell.risk_score / maxRisk) * 100);
                    const color = pct >= 75 ? 'var(--color-danger)' : pct >= 40 ? 'var(--color-warning)' : 'var(--color-success)';
                    html += `<div class="ai-risk-heatmap__cell" style="background:${color}; opacity:${0.3 + pct/140}" title="Risk: ${cell.risk_score}">
                        <strong>${cell.module || '?'}</strong>
                        <span>${cell.layer || ''}</span>
                        <span class="ai-risk-heatmap__score">${cell.risk_score}</span>
                    </div>`;
                });
                html += '</div>';
            }

            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
        }
    }

    // ── TC Maintenance ──────────────────────────────────────────────────
    function _renderTCMaintenance(container) {
        container.innerHTML = `
            <div class="card" style="margin-top:var(--space-4)">
                <div class="card-header">
                    <h2>🔧 Test Case Maintenance Advisor</h2>
                    <button class="btn btn-primary btn-sm" onclick="AIInsightsView.runTCMaintenance()">Scan</button>
                </div>
                <div class="card-body" id="tcMaintenanceResult">
                    <p class="text-muted">Scan for stale, never-executed, unlinked, and duplicate test cases.</p>
                </div>
            </div>
        `;
    }

    async function runTCMaintenance() {
        const container = document.getElementById('tcMaintenanceResult');
        container.innerHTML = '<div class="spinner"></div>';

        try {
            const resp = await fetch(`/api/v1/ai/programs/${programId}/tc-maintenance`);
            const data = await resp.json();

            if (data.error) {
                container.innerHTML = `<div class="alert alert-warning">${data.error}</div>`;
                return;
            }

            const summary = data.summary || {};
            let html = `
                <div class="ai-insights-summary-cards">
                    <div class="ai-insights-stat"><span class="ai-insights-stat__value">${summary.total_test_cases || 0}</span><span class="ai-insights-stat__label">Total TCs</span></div>
                    <div class="ai-insights-stat ai-insights-stat--danger"><span class="ai-insights-stat__value">${summary.never_executed_count || 0}</span><span class="ai-insights-stat__label">Never Executed</span></div>
                    <div class="ai-insights-stat ai-insights-stat--warning"><span class="ai-insights-stat__value">${summary.stale_count || 0}</span><span class="ai-insights-stat__label">Stale (90d+)</span></div>
                    <div class="ai-insights-stat ai-insights-stat--info"><span class="ai-insights-stat__value">${summary.unlinked_count || 0}</span><span class="ai-insights-stat__label">Unlinked</span></div>
                    <div class="ai-insights-stat"><span class="ai-insights-stat__value">${summary.duplicate_groups || 0}</span><span class="ai-insights-stat__label">Duplicate Groups</span></div>
                </div>
                <p style="margin-top:var(--space-3);font-style:italic">${summary.message || ''}</p>
            `;

            // Never executed list
            const never = data.never_executed || [];
            if (never.length) {
                html += `<h3 style="margin-top:var(--space-4)">⚠️ Never Executed (${never.length})</h3>`;
                html += '<table class="table"><thead><tr><th>Code</th><th>Title</th><th>Module</th><th>Recommendation</th></tr></thead><tbody>';
                never.forEach(n => {
                    html += `<tr><td><strong>${n.code}</strong></td><td>${n.title}</td><td>${n.module || ''}</td><td>${n.recommendation}</td></tr>`;
                });
                html += '</tbody></table>';
            }

            // Stale list
            const stale = data.stale || [];
            if (stale.length) {
                html += `<h3 style="margin-top:var(--space-4)">📅 Stale Tests (${stale.length})</h3>`;
                html += '<table class="table"><thead><tr><th>Code</th><th>Title</th><th>Last Executed</th><th>Days Since</th><th>Recommendation</th></tr></thead><tbody>';
                stale.forEach(s => {
                    html += `<tr><td><strong>${s.code}</strong></td><td>${s.title}</td><td>${s.last_executed_at || ''}</td><td>${s.days_since}</td><td>${s.recommendation}</td></tr>`;
                });
                html += '</tbody></table>';
            }

            // Duplicates
            const dupes = data.duplicates || [];
            if (dupes.length) {
                html += `<h3 style="margin-top:var(--space-4)">🔁 Possible Duplicates (${dupes.length} groups)</h3>`;
                dupes.forEach((group, i) => {
                    html += `<div class="card" style="margin-top:var(--space-2);padding:var(--space-3)"><strong>Group ${i + 1}:</strong><ul>`;
                    group.forEach(g => html += `<li>${g.code} — ${g.title}</li>`);
                    html += '</ul></div>';
                });
            }

            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
        }
    }

    // ── Global Smart Search (⌘K / Ctrl+K) ───────────────────────────────
    function _initGlobalSearch() {
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                _openGlobalSearchModal();
            }
        });
    }

    function _openGlobalSearchModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        if (!overlay || !modal) return;

        overlay.classList.add('active');
        modal.innerHTML = `
            <div class="ai-global-search-modal">
                <div class="ai-global-search-modal__header">
                    <span>🔍 Smart Search</span>
                    <button class="btn btn-sm" onclick="AIInsightsView.closeGlobalSearch()">✕</button>
                </div>
                <input type="text" id="aiGlobalSearchInput" class="tm-input" 
                    placeholder="Search test cases, defects, executions..." autofocus
                    style="width:100%;margin:var(--space-3) 0"/>
                <div id="aiGlobalSearchResults" style="max-height:400px;overflow-y:auto"></div>
            </div>
        `;

        const input = document.getElementById('aiGlobalSearchInput');
        let _debounce;
        input?.addEventListener('input', () => {
            clearTimeout(_debounce);
            _debounce = setTimeout(() => _globalSearchExecute(input.value), 350);
        });
        input?.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeGlobalSearch();
        });
    }

    async function _globalSearchExecute(query) {
        const container = document.getElementById('aiGlobalSearchResults');
        if (!container) return;
        query = (query || '').trim();
        if (query.length < 2) { container.innerHTML = ''; return; }

        const prog = App.getActiveProgram();
        const pid = prog ? prog.id : null;
        if (!pid) { container.innerHTML = '<p class="text-muted">Please select a program first.</p>'; return; }

        container.innerHTML = '<div class="spinner spinner--sm"></div>';
        try {
            const resp = await fetch('/api/v1/ai/smart-search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, program_id: pid }),
            });
            const data = await resp.json();

            let html = '';
            ['test_cases', 'defects', 'executions'].forEach(key => {
                const items = data[key] || [];
                items.slice(0, 5).forEach(item => {
                    const label = item.code || item.title || item.id;
                    const subtitle = item.title || item.module || '';
                    html += `<div class="ai-global-search-result-item"
                                onclick="AIInsightsView.closeGlobalSearch()">
                        <strong>${label}</strong> <span class="text-muted">${subtitle}</span>
                    </div>`;
                });
            });
            container.innerHTML = html || '<p class="text-muted">No results</p>';
        } catch {
            container.innerHTML = '<p class="text-muted">Search unavailable</p>';
        }
    }

    function closeGlobalSearch() {
        const overlay = document.getElementById('modalOverlay');
        overlay?.classList.remove('active');
    }

    // ── Init ─────────────────────────────────────────────────────────────
    // Register global ⌘K listener on load
    if (typeof document !== 'undefined') {
        document.addEventListener('DOMContentLoaded', _initGlobalSearch);
    }

    return {
        render,
        switchTab,
        runSmartSearch,
        runFlakyDetection,
        runPredictiveCoverage,
        runTCMaintenance,
        closeGlobalSearch,
    };
})();
