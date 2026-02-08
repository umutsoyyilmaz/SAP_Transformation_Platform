/**
 * SAP Transformation Platform — Sprint 8
 * AI Query View — Chat-style NL Query interface.
 *
 * Features:
 *   - Natural-language query input (TR/EN)
 *   - SAP glossary term hints
 *   - SQL preview + confidence badge
 *   - Results table
 *   - Query history sidebar
 */

const AIQueryView = (() => {
    let history = [];
    let currentProgramId = null;

    // ── Render ────────────────────────────────────────────────────────────
    function render() {
        currentProgramId = document.getElementById('globalProjectSelector')?.value || null;

        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <h1>🤖 AI Query Assistant</h1>
                <p class="page-header__sub">Ask questions about your SAP transformation data in natural language.</p>
            </div>

            <div class="ai-query-layout">
                <!-- Query Panel -->
                <div class="ai-query-panel">
                    <!-- Input Area -->
                    <div class="card ai-query-input-card">
                        <div class="card-header"><h2>Ask a Question</h2></div>
                        <div class="ai-query-input-area">
                            <textarea id="aiQueryInput" 
                                placeholder="e.g. How many P1 defects are open in FI module?&#10;e.g. List all gap requirements for program 1&#10;e.g. Show WRICEF backlog items by status"
                                rows="3"></textarea>
                            <div class="ai-query-actions">
                                <label class="ai-query-toggle">
                                    <input type="checkbox" id="aiAutoExecute" checked>
                                    Auto-execute
                                </label>
                                <button class="btn btn-primary" id="aiQueryBtn" onclick="AIQueryView.submitQuery()">
                                    🔍 Query
                                </button>
                            </div>
                        </div>
                        <div class="ai-query-hints">
                            <strong>💡 Tips:</strong>
                            <span class="hint-chip" onclick="AIQueryView.useHint(this)">How many open defects?</span>
                            <span class="hint-chip" onclick="AIQueryView.useHint(this)">List all P1 defects in FI</span>
                            <span class="hint-chip" onclick="AIQueryView.useHint(this)">Requirements by fit/gap status</span>
                            <span class="hint-chip" onclick="AIQueryView.useHint(this)">WRICEF items by module</span>
                            <span class="hint-chip" onclick="AIQueryView.useHint(this)">Test execution pass rate</span>
                        </div>
                    </div>

                    <!-- Result Area -->
                    <div id="aiQueryResult" class="ai-query-result"></div>
                </div>

                <!-- History Sidebar -->
                <div class="ai-query-history card">
                    <div class="card-header"><h2>History</h2></div>
                    <div id="aiQueryHistory" class="ai-query-history-list">
                        <div class="empty-state" style="padding:1rem">
                            <p>No queries yet</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // ── Submit Query ──────────────────────────────────────────────────────
    async function submitQuery() {
        const input = document.getElementById('aiQueryInput');
        const query = input.value.trim();
        if (!query) return;

        const autoExecute = document.getElementById('aiAutoExecute').checked;
        const resultDiv = document.getElementById('aiQueryResult');
        const btn = document.getElementById('aiQueryBtn');

        // Loading state
        btn.disabled = true;
        btn.textContent = '⏳ Processing...';
        resultDiv.innerHTML = `
            <div class="card">
                <div class="ai-query-loading">
                    <div class="spinner"></div>
                    <p>AI is analyzing your query...</p>
                </div>
            </div>
        `;

        try {
            const payload = {
                query: query,
                auto_execute: autoExecute,
            };
            if (currentProgramId) payload.program_id = parseInt(currentProgramId);

            const data = await API.post('/ai/query/natural-language', payload);
            renderResult(data);
            addToHistory(query, data);
        } catch (err) {
            resultDiv.innerHTML = `
                <div class="card">
                    <div class="ai-query-error">
                        <strong>⚠️ Error:</strong> ${escHtml(err.message || 'Query failed')}
                    </div>
                </div>
            `;
        } finally {
            btn.disabled = false;
            btn.textContent = '🔍 Query';
        }
    }

    // ── Render Result ────────────────────────────────────────────────────
    function renderResult(data) {
        const resultDiv = document.getElementById('aiQueryResult');
        const confidenceClass = data.confidence >= 0.8 ? 'high' : data.confidence >= 0.5 ? 'medium' : 'low';
        const confidencePct = Math.round(data.confidence * 100);

        let glossaryHtml = '';
        if (data.glossary_matches && data.glossary_matches.length > 0) {
            glossaryHtml = `
                <div class="ai-query-glossary">
                    <strong>📖 SAP Terms Detected:</strong>
                    ${data.glossary_matches.map(g => `<span class="glossary-chip">${escHtml(g.term)}${g.alias ? ` (${escHtml(g.alias)})` : ''}</span>`).join('')}
                </div>
            `;
        }

        let sqlHtml = '';
        if (data.sql) {
            sqlHtml = `
                <div class="ai-query-sql">
                    <div class="ai-query-sql-header">
                        <strong>📝 Generated SQL</strong>
                        <span class="badge badge-confidence-${confidenceClass}">Confidence: ${confidencePct}%</span>
                    </div>
                    <pre class="sql-code">${escHtml(data.sql)}</pre>
                    ${!data.executed ? `
                        <button class="btn btn-sm btn-primary" onclick="AIQueryView.executeSQL()">
                            ▶️ Execute
                        </button>
                    ` : ''}
                </div>
            `;
        }

        let explanationHtml = '';
        if (data.explanation) {
            explanationHtml = `
                <div class="ai-query-explanation">
                    <strong>💬 Explanation:</strong> ${escHtml(data.explanation)}
                </div>
            `;
        }

        let tableHtml = '';
        if (data.executed && data.results && data.results.length > 0) {
            const cols = data.columns || Object.keys(data.results[0]);
            tableHtml = `
                <div class="ai-query-results-table">
                    <div class="ai-query-results-header">
                        <strong>📊 Results</strong>
                        <span class="badge">${data.row_count} row${data.row_count !== 1 ? 's' : ''}</span>
                    </div>
                    <div class="table-scroll">
                        <table class="data-table">
                            <thead>
                                <tr>${cols.map(c => `<th>${escHtml(c)}</th>`).join('')}</tr>
                            </thead>
                            <tbody>
                                ${data.results.map(row => `
                                    <tr>${cols.map(c => `<td>${escHtml(String(row[c] ?? ''))}</td>`).join('')}</tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } else if (data.executed && data.row_count === 0) {
            tableHtml = `
                <div class="ai-query-no-results">
                    <p>Query executed successfully but returned no results.</p>
                </div>
            `;
        }

        let errorHtml = '';
        if (data.error) {
            errorHtml = `
                <div class="ai-query-warning">
                    <strong>⚠️</strong> ${escHtml(data.error)}
                </div>
            `;
        }

        resultDiv.innerHTML = `
            <div class="card ai-query-result-card">
                ${glossaryHtml}
                ${explanationHtml}
                ${sqlHtml}
                ${errorHtml}
                ${tableHtml}
            </div>
        `;

        // Store current SQL for manual execute
        resultDiv.dataset.currentSql = data.sql || '';
        resultDiv.dataset.programId = data.program_id || '';
    }

    // ── Manual SQL Execute ───────────────────────────────────────────────
    async function executeSQL() {
        const resultDiv = document.getElementById('aiQueryResult');
        const sql = resultDiv.dataset.currentSql;
        if (!sql) return;

        try {
            const payload = { sql: sql };
            if (resultDiv.dataset.programId) {
                payload.program_id = parseInt(resultDiv.dataset.programId);
            }
            const data = await API.post('/ai/query/execute-sql', payload);
            // Re-render with execution results
            renderResult({
                ...data,
                sql: sql,
                executed: true,
                confidence: 1.0,
                explanation: 'Manual execution completed.',
            });
        } catch (err) {
            App.toast('SQL execution failed: ' + err.message, 'error');
        }
    }

    // ── History ──────────────────────────────────────────────────────────
    function addToHistory(query, result) {
        history.unshift({
            query: query,
            timestamp: new Date().toLocaleTimeString(),
            success: !result.error || result.executed,
            rowCount: result.row_count || 0,
        });
        if (history.length > 20) history.pop();
        renderHistory();
    }

    function renderHistory() {
        const el = document.getElementById('aiQueryHistory');
        if (!history.length) {
            el.innerHTML = '<div class="empty-state" style="padding:1rem"><p>No queries yet</p></div>';
            return;
        }
        el.innerHTML = history.map((h, i) => `
            <div class="ai-history-item ${h.success ? '' : 'error'}" onclick="AIQueryView.replayHistory(${i})">
                <div class="ai-history-query">${escHtml(h.query.substring(0, 60))}${h.query.length > 60 ? '...' : ''}</div>
                <div class="ai-history-meta">
                    <span>${h.timestamp}</span>
                    <span>${h.rowCount} rows</span>
                </div>
            </div>
        `).join('');
    }

    function replayHistory(index) {
        const item = history[index];
        if (!item) return;
        document.getElementById('aiQueryInput').value = item.query;
    }

    // ── Hint chips ───────────────────────────────────────────────────────
    function useHint(el) {
        document.getElementById('aiQueryInput').value = el.textContent;
    }

    // ── Utility ──────────────────────────────────────────────────────────
    function escHtml(str) {
        const d = document.createElement('div');
        d.textContent = str ?? '';
        return d.innerHTML;
    }

    return { render, submitQuery, executeSQL, useHint, replayHistory };
})();
