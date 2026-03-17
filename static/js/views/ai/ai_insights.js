/**
 * SAP Transformation Platform — F4
 * AI Insights View — Smart Search (⌘K), Flaky Tests, Predictive Coverage,
 *                     Suite Optimizer, TC Maintenance.
 *
 * Vanilla JS IIFE pattern matching project conventions.
 */

const AIInsightsView = (() => {
    const SMART_SEARCH_QUERY_KEY = 'pg.aiSmartSearchQuery';
    let programId = null;
    let _activeTab = 'smart-search';

    // ── Render ───────────────────────────────────────────────────────────
    function render() {
        const prog = App.getActiveProgram();
        programId = prog ? prog.id : null;
        const pendingSmartSearch = _readPendingSmartSearch();
        if (pendingSmartSearch) _activeTab = 'smart-search';

        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'AI Insights' }])}
                <h2 class="pg-view-title">AI Insights</h2>
                <p class="ai-page-copy">Smart search, flaky-test detection, predictive coverage & maintenance.</p>
            </div>

            <!-- Tab Bar -->
            <div class="tm-tab-bar ai-insights-tabs">
                <button class="tm-tab-bar__tab ${_activeTab === 'smart-search' ? 'active' : ''}" data-tab="smart-search" onclick="AIInsightsView.switchTab('smart-search')">🔍 Smart Search</button>
                <button class="tm-tab-bar__tab ${_activeTab === 'flaky-tests' ? 'active' : ''}" data-tab="flaky-tests" onclick="AIInsightsView.switchTab('flaky-tests')">⚡ Flaky Tests</button>
                <button class="tm-tab-bar__tab ${_activeTab === 'predictive-coverage' ? 'active' : ''}" data-tab="predictive-coverage" onclick="AIInsightsView.switchTab('predictive-coverage')">🎯 Risk Heatmap</button>
                <button class="tm-tab-bar__tab ${_activeTab === 'tc-maintenance' ? 'active' : ''}" data-tab="tc-maintenance" onclick="AIInsightsView.switchTab('tc-maintenance')">🔧 TC Maintenance</button>
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
        const pendingSmartSearch = _consumePendingSmartSearch();
        container.innerHTML = `
            <div class="card ai-card">
                <div class="card-header"><h2>🔍 Natural Language Smart Search</h2></div>
                <div class="card-body">
                    <div class="ai-insights-search-bar">
                        <input type="text" id="aiSmartSearchInput" class="tm-input ai-search-input"
                            placeholder="e.g. 'P1 test cases that failed in the FI module'"
                        />
                        <button class="btn btn-primary" onclick="AIInsightsView.runSmartSearch()">Search</button>
                    </div>
                    <p class="text-muted ai-admin-total">
                        Tip: Use <kbd>⌘K</kbd> / <kbd>Ctrl+K</kbd> to open smart search from anywhere.
                    </p>
                    <div id="aiSmartSearchResults" class="ai-result-slot"></div>
                </div>
            </div>
        `;
        setTimeout(() => {
            const input = document.getElementById('aiSmartSearchInput');
            input?.focus();
            if (input && pendingSmartSearch) {
                input.value = pendingSmartSearch;
                runSmartSearch();
            }
        }, 100);
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
                html += `<h3 class="ai-section-title">Results (${items.length})</h3>`;
                html += '<table class="data-table" aria-label="AI query results"><thead><tr>';
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
            <div class="card ai-card">
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
                html += '<table class="data-table ai-result-slot" aria-label="Flaky tests analysis"><thead><tr><th>Code</th><th>Title</th><th>Flakiness</th><th>Env Correlation</th><th>Recommendation</th></tr></thead><tbody>';
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
                html += '<div class="alert alert-success ai-success-note">No flaky tests detected! ✓</div>';
            }

            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
        }
    }

    // ── Predictive Coverage / Risk Heatmap ──────────────────────────────
    function _renderPredictiveCoverage(container) {
        container.innerHTML = `
            <div class="card ai-card">
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
                html += '<h3 class="ai-section-title">Risk Heatmap</h3>';
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
            <div class="card ai-card">
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
                <p class="ai-summary-note">${summary.message || ''}</p>
            `;

            // Never executed list
            const never = data.never_executed || [];
            if (never.length) {
                html += `<h3 class="ai-section-title">⚠️ Never Executed (${never.length})</h3>`;
                html += '<table class="data-table" aria-label="Obsolete tests"><thead><tr><th>Code</th><th>Title</th><th>Module</th><th>Recommendation</th></tr></thead><tbody>';
                never.forEach(n => {
                    html += `<tr><td><strong>${n.code}</strong></td><td>${n.title}</td><td>${n.module || ''}</td><td>${n.recommendation}</td></tr>`;
                });
                html += '</tbody></table>';
            }

            // Stale list
            const stale = data.stale || [];
            if (stale.length) {
                html += `<h3 class="ai-section-title">📅 Stale Tests (${stale.length})</h3>`;
                html += '<table class="data-table" aria-label="Stale tests"><thead><tr><th>Code</th><th>Title</th><th>Last Executed</th><th>Days Since</th><th>Recommendation</th></tr></thead><tbody>';
                stale.forEach(s => {
                    html += `<tr><td><strong>${s.code}</strong></td><td>${s.title}</td><td>${s.last_executed_at || ''}</td><td>${s.days_since}</td><td>${s.recommendation}</td></tr>`;
                });
                html += '</tbody></table>';
            }

            // Duplicates
            const dupes = data.duplicates || [];
            if (dupes.length) {
                html += `<h3 class="ai-section-title">🔁 Possible Duplicates (${dupes.length} groups)</h3>`;
                dupes.forEach((group, i) => {
                    html += `<div class="card ai-duplicate-card"><strong>Group ${i + 1}:</strong><ul>`;
                    group.forEach(g => html += `<li>${g.code} — ${g.title}</li>`);
                    html += '</ul></div>';
                });
            }

            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
        }
    }

    function _readPendingSmartSearch() {
        try {
            return sessionStorage.getItem(SMART_SEARCH_QUERY_KEY) || '';
        } catch {
            return '';
        }
    }

    function _consumePendingSmartSearch() {
        const query = _readPendingSmartSearch();
        if (!query) return '';
        try {
            sessionStorage.removeItem(SMART_SEARCH_QUERY_KEY);
        } catch {
            // Ignore sessionStorage failures.
        }
        return query;
    }

    return {
        render,
        switchTab,
        runSmartSearch,
        runFlakyDetection,
        runPredictiveCoverage,
        runTCMaintenance,
    };
})();
