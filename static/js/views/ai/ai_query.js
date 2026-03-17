/**
 * SAP Transformation Platform
 * AI Query View — answer-first chatbot UI with saved conversations.
 */

const AIQueryView = (() => {
    let messages = [];
    let conversations = [];
    let activeConversationId = null;
    let currentProgramId = null;
    let currentProjectId = null;

    const STORAGE_KEY_PREFIX = 'aiQueryConversation';
    const DEFAULT_HINTS = [
        'How many open defects?',
        'How many risk items are under this project?',
        'Requirements by fit/gap status',
        'How many RFCs do we have in this project?',
    ];

    async function render() {
        const program = App.getActiveProgram();
        const project = App.getActiveProject ? App.getActiveProject() : null;
        currentProgramId = program ? program.id : null;
        currentProjectId = project ? project.id : null;

        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'AI Query Assistant' }])}
                <h2 class="pg-view-title">AI Query Assistant</h2>
            </div>

            <div class="ai-query-layout ai-query-layout--chat">
                <div class="ai-query-panel ai-query-panel--chat">
                    <div class="card ai-query-chat-shell">
                        <div class="ai-query-chat-header">
                            <div>
                                <h2>Ask the transformation copilot</h2>
                                <p>Ask in plain language. You will get a direct answer first, and technical details only if you ask for them.</p>
                            </div>
                            <div class="ai-query-context">
                                <span class="ai-query-context-badge ${currentProgramId ? '' : 'is-muted'}">Program ${currentProgramId || 'Not selected'}</span>
                                <span class="ai-query-context-badge ${currentProjectId ? '' : 'is-muted'}">Project ${currentProjectId || 'Not selected'}</span>
                            </div>
                        </div>

                        <div id="aiQueryThread" class="ai-query-thread"></div>
                        <div id="aiQueryHints" class="ai-query-hints ai-query-hints--chat"></div>

                        <div class="ai-query-composer">
                            <textarea id="aiQueryInput"
                                placeholder="Ask about risks, defects, requirements, RFCs, workshops, or test cases."
                                rows="3"></textarea>
                            <div class="ai-query-actions ai-query-actions--chat">
                                <button class="btn btn-primary" id="aiQueryBtn" onclick="AIQueryView.submitQuery()">
                                    Send
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="ai-query-history card">
                    <div class="card-header"><h2>Conversation History</h2></div>
                    <div id="aiQueryHistory" class="ai-query-history-list">
                        ${PGEmptyState.html({ icon: 'ai', title: 'No conversations yet', description: 'Your saved chat sessions will appear here.' })}
                    </div>
                </div>
            </div>
        `;

        bindComposerShortcuts();
        renderThread();
        renderDynamicHints();
        await initializeConversationState();
    }

    async function submitQuery() {
        const input = document.getElementById('aiQueryInput');
        const query = input.value.trim();
        if (!query) return;

        const btn = document.getElementById('aiQueryBtn');
        const pendingId = `pending-${Date.now()}`;
        const wantsRefinement = shouldUseRefinement(query);
        const conversationId = await ensureConversation(query);
        if (!conversationId) return;

        messages.push({
            id: `user-${Date.now()}`,
            role: 'user',
            query,
            timestamp: new Date().toLocaleTimeString(),
        });
        messages.push({
            id: pendingId,
            role: 'assistant',
            state: 'loading',
            timestamp: new Date().toLocaleTimeString(),
        });
        renderThread();
        input.value = '';

        btn.disabled = true;
        btn.textContent = 'Thinking...';

        try {
            const data = await executeQueryRequest(query, conversationId, wantsRefinement);
            activeConversationId = data.conversation_id || conversationId;
            persistActiveConversationId(activeConversationId);
            upsertAssistantMessage(pendingId, data);
            await refreshConversationList();
            renderDynamicHints();
        } catch (err) {
            upsertAssistantMessage(pendingId, {
                answer: err.message || 'Query failed',
                error: err.message || 'Query failed',
                suggestions: DEFAULT_HINTS,
                executed: false,
                results: [],
                row_count: 0,
                columns: [],
                confidence: 0,
                glossary_matches: [],
            });
        } finally {
            btn.disabled = false;
            btn.textContent = 'Send';
        }
    }

    async function executeQueryRequest(query, conversationId, wantsRefinement) {
        const requestConfig = buildQueryRequest(query, conversationId, wantsRefinement);
        try {
            return await API.post(requestConfig.endpoint, requestConfig.payload);
        } catch (err) {
            if (wantsRefinement && shouldRetryAsFreshQuery(err)) {
                const routingNote = 'This message was handled as a new question because the previous result could not be refined directly.';
                const fallbackConfig = buildQueryRequest(query, conversationId, false, {
                    routing_note: routingNote,
                    routed_as_fresh_query: true,
                });
                return API.post(fallbackConfig.endpoint, fallbackConfig.payload);
            }
            throw err;
        }
    }

    function buildQueryRequest(query, conversationId, wantsRefinement, extraPayload = {}) {
        if (wantsRefinement) {
            return {
                endpoint: '/ai/query/refine',
                payload: {
                    conversation_id: conversationId,
                    refinement: query,
                },
            };
        }

        const payload = {
            query,
            auto_execute: true,
            conversation_id: conversationId,
            ...extraPayload,
        };
        if (currentProgramId) payload.program_id = parseInt(currentProgramId, 10);
        if (currentProjectId) payload.project_id = parseInt(currentProjectId, 10);

        return {
            endpoint: '/ai/query/natural-language',
            payload,
        };
    }

    function shouldUseRefinement(query) {
        if (!activeConversationId) return false;
        if (!messages.some((message) => message.role === 'assistant' && message.data?.type === 'nl_query_result')) {
            return false;
        }

        const normalized = query.toLowerCase().trim();
        const conversationalPrefix = '(?:then|and|also|now)\\s+';
        return new RegExp(`^(?:${conversationalPrefix})?(only|just|show top|top\\s+\\d+|first\\s+\\d+|limit\\s+\\d+|sort|sorted by|order by|group by|filter|now show|by status|by module|by priority|for\\s+[a-z0-9_ -]+|last\\s+\\d+\\s+(day|days|week|weeks|month|months)|today|this week|this month)`).test(normalized);
    }

    function shouldRetryAsFreshQuery(err) {
        const message = String(err?.message || '').toLowerCase();
        return message.includes('single count result')
            || message.includes('does not apply to a single count result')
            || message.includes('turn that count into a detailed list')
            || message.includes('already a detailed view');
    }

    function upsertAssistantMessage(id, data) {
        const index = messages.findIndex((message) => message.id === id);
        const assistantMessage = {
            id,
            role: 'assistant',
            data,
            timestamp: new Date().toLocaleTimeString(),
        };
        if (index >= 0) messages[index] = assistantMessage;
        else messages.push(assistantMessage);
        renderThread();
    }

    function renderThread() {
        const thread = document.getElementById('aiQueryThread');
        if (!thread) return;

        if (!messages.length) {
            thread.innerHTML = `
                <div class="ai-query-empty-state ai-query-empty-state--thread">
                    <h3>Start a conversation</h3>
                    <p>Ask a question about the active program or project. You will get a direct answer and can open technical details only when needed.</p>
                </div>
            `;
            return;
        }

        thread.innerHTML = messages.map((message) => renderMessage(message)).join('');
        thread.scrollTop = thread.scrollHeight;
    }

    function renderMessage(message) {
        if (message.role === 'user') {
            return `
                <article class="ai-message ai-message--user">
                    <div class="ai-message-meta">You • ${escHtml(message.timestamp || '')}</div>
                    <div class="ai-message-bubble">${escHtml(message.query || '')}</div>
                </article>
            `;
        }

        if (message.state === 'loading') {
            return `
                <article class="ai-message ai-message--assistant">
                    <div class="ai-message-meta">Assistant • ${escHtml(message.timestamp || '')}</div>
                    <div class="ai-message-bubble ai-message-bubble--loading">
                        <div class="ai-query-loading">
                            <div class="spinner"></div>
                            <p>Analyzing your question and preparing the answer.</p>
                        </div>
                    </div>
                </article>
            `;
        }

        return `
            <article class="ai-message ai-message--assistant">
                <div class="ai-message-meta">Assistant • ${escHtml(message.timestamp || '')}</div>
                <div class="ai-message-bubble ai-message-bubble--assistant">
                    ${renderAssistantContent(message.data || {})}
                </div>
            </article>
        `;
    }

    function renderAssistantContent(data) {
        const confidenceClass = data.confidence >= 0.8 ? 'high' : data.confidence >= 0.5 ? 'medium' : 'low';
        const confidencePct = Math.round((data.confidence || 0) * 100);
        const detailId = `detail-${Math.random().toString(36).slice(2, 10)}`;

        const answerHtml = `
            <div class="ai-query-answer">
                <strong>Answer:</strong> ${escHtml(data.answer || 'No answer generated.')}
            </div>
        `;

        const routingHtml = data.routing_note ? `
            <div class="ai-query-routing-note">
                <strong>Handled as new question</strong>
                <span>${escHtml(data.routing_note)}</span>
            </div>
        ` : '';

        const glossaryHtml = Array.isArray(data.glossary_matches) && data.glossary_matches.length ? `
            <div class="ai-query-glossary">
                <strong>SAP terms detected:</strong>
                ${data.glossary_matches.map((match) => `<span class="glossary-chip">${escHtml(match.term)}${match.alias ? ` (${escHtml(match.alias)})` : ''}</span>`).join('')}
            </div>
        ` : '';

        const explanationHtml = data.explanation ? `
            <div class="ai-query-explanation">
                <strong>Explanation:</strong> ${escHtml(data.explanation)}
            </div>
        ` : '';

        const suggestionsHtml = Array.isArray(data.suggestions) && data.suggestions.length ? `
            <div class="ai-query-glossary ai-query-suggestions">
                <strong>Try next:</strong>
                ${data.suggestions.map((suggestion) => `<span class="hint-chip" onclick="AIQueryView.useSuggestion(${JSON.stringify(suggestion).replace(/"/g, '&quot;')})">${escHtml(suggestion)}</span>`).join('')}
            </div>
        ` : '';

        const sqlHtml = data.sql ? `
            <div class="ai-query-sql">
                <div class="ai-query-sql-header">
                    <strong>Generated SQL</strong>
                    <span class="badge badge-confidence-${confidenceClass}">Confidence: ${confidencePct}%</span>
                </div>
                <pre class="sql-code">${escHtml(data.sql)}</pre>
                ${!data.executed ? `
                    <button class="btn btn-sm btn-primary" onclick="AIQueryView.executeSQL(${JSON.stringify(data.sql).replace(/"/g, '&quot;')}, ${Number(data.program_id || currentProgramId || 0)}, ${Number(data.project_id || currentProjectId || 0)})">
                        Execute SQL
                    </button>
                ` : ''}
            </div>
        ` : '';

        const errorHtml = data.error ? `
            <div class="ai-query-warning">
                <strong>Attention:</strong> ${escHtml(data.error)}
            </div>
        ` : '';

        let resultHtml = '';
        if (data.executed && Array.isArray(data.results) && data.results.length > 0) {
            const columns = data.columns || Object.keys(data.results[0]);
            resultHtml = `
                <div class="ai-query-results-table">
                    <div class="ai-query-results-header">
                        <strong>Results</strong>
                        <span class="badge">${data.row_count} row${data.row_count === 1 ? '' : 's'}</span>
                    </div>
                    <div class="table-scroll">
                        <table class="data-table">
                            <thead>
                                <tr>${columns.map((column) => `<th>${escHtml(column)}</th>`).join('')}</tr>
                            </thead>
                            <tbody>
                                ${data.results.map((row) => `
                                    <tr>${columns.map((column) => `<td>${escHtml(String(row[column] ?? ''))}</td>`).join('')}</tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } else if (data.executed && data.row_count === 0) {
            resultHtml = `
                <div class="ai-query-no-results">
                    <p>Query executed successfully but returned no matching rows.</p>
                </div>
            `;
        }

        const hasDetails = Boolean(glossaryHtml || explanationHtml || suggestionsHtml || sqlHtml || errorHtml || resultHtml);
        const detailToggle = hasDetails ? `
            <button class="btn btn-secondary btn-sm ai-query-detail-toggle" onclick="AIQueryView.toggleDetails('${detailId}')">
                Show details
            </button>
        ` : '';
        const detailPanel = hasDetails ? `
            <div id="${detailId}" class="ai-query-details is-hidden">
                ${glossaryHtml}
                ${explanationHtml}
                ${suggestionsHtml}
                ${sqlHtml}
                ${errorHtml}
                ${resultHtml}
            </div>
        ` : '';

        return `
            <div class="ai-query-result-card">
                ${answerHtml}
                ${routingHtml}
                ${detailToggle}
                ${detailPanel}
            </div>
        `;
    }

    async function executeSQL(sql, programId, projectId) {
        if (!sql) return;
        try {
            const payload = { sql };
            if (programId) payload.program_id = parseInt(programId, 10);
            if (projectId) payload.project_id = parseInt(projectId, 10);

            const data = await API.post('/ai/query/execute-sql', payload);
            messages.push({
                id: `assistant-manual-${Date.now()}`,
                role: 'assistant',
                timestamp: new Date().toLocaleTimeString(),
                data: {
                    ...data,
                    sql,
                    executed: true,
                    confidence: 1.0,
                    explanation: 'Manual execution completed.',
                    answer: `Manual execution returned ${data.row_count || 0} row${data.row_count === 1 ? '' : 's'}.`,
                    program_id: programId || currentProgramId,
                    project_id: projectId || currentProjectId,
                },
            });
            renderThread();
        } catch (err) {
            App.toast('SQL execution failed: ' + err.message, 'error');
        }
    }

    function renderHistory() {
        const historyEl = document.getElementById('aiQueryHistory');
        if (!historyEl) return;

        if (!conversations.length) {
            historyEl.innerHTML = '<div class="empty-state ai-query-empty-state"><p>No conversations yet</p></div>';
            return;
        }

        historyEl.innerHTML = conversations.map((conversation) => `
            <div class="ai-history-item ${conversation.id === activeConversationId ? 'is-active' : ''}" onclick="AIQueryView.openConversation(${conversation.id})">
                <div class="ai-history-query">${escHtml(conversation.title || 'Untitled conversation')}</div>
                <div class="ai-history-meta">
                    <span>${formatRelativeTime(conversation.updated_at || conversation.created_at)}</span>
                    <span>${conversation.message_count || 0} msgs</span>
                </div>
            </div>
        `).join('');
    }

    async function openConversation(conversationId) {
        if (!conversationId) return;
        activeConversationId = conversationId;
        persistActiveConversationId(conversationId);
        await loadConversation(conversationId);
    }

    function useHint(el) {
        document.getElementById('aiQueryInput').value = el.textContent;
        document.getElementById('aiQueryInput').focus();
    }

    function useSuggestion(text) {
        document.getElementById('aiQueryInput').value = text;
        document.getElementById('aiQueryInput').focus();
    }

    async function initializeConversationState() {
        try {
            await refreshConversationList();

            const storedConversationId = readStoredConversationId();
            if (storedConversationId && conversations.some((conversation) => conversation.id === storedConversationId)) {
                activeConversationId = storedConversationId;
                await loadConversation(storedConversationId);
                return;
            }

            if (conversations.length) {
                activeConversationId = conversations[0].id;
                persistActiveConversationId(activeConversationId);
                await loadConversation(activeConversationId);
                return;
            }

            renderHistory();
        } catch (err) {
            App.toast('Conversation history could not be loaded: ' + err.message, 'error');
        }
    }

    async function refreshConversationList() {
        const queryParts = ['assistant_type=nl_query', 'limit=20'];
        if (currentProgramId) queryParts.push(`program_id=${encodeURIComponent(currentProgramId)}`);
        const rows = await API.get(`/ai/conversations?${queryParts.join('&')}`);
        conversations = (Array.isArray(rows) ? rows : []).filter((conversation) => {
            const context = conversation.context || {};
            if (!currentProjectId) return true;
            return !context.project_id || Number(context.project_id) === Number(currentProjectId);
        });
        renderHistory();
    }

    async function ensureConversation(initialQuery) {
        if (activeConversationId) return activeConversationId;

        try {
            const payload = {
                assistant_type: 'nl_query',
                title: buildConversationTitle(initialQuery),
                context: {
                    project_id: currentProjectId || null,
                    auto_execute: true,
                },
            };
            if (currentProgramId) payload.program_id = parseInt(currentProgramId, 10);

            const conversation = await API.post('/ai/conversations', payload);
            activeConversationId = conversation.id;
            persistActiveConversationId(activeConversationId);
            await refreshConversationList();
            return activeConversationId;
        } catch (err) {
            App.toast('Conversation could not be started: ' + err.message, 'error');
            return null;
        }
    }

    async function loadConversation(conversationId) {
        const conversation = await API.get(`/ai/conversations/${conversationId}?messages=true`);
        messages = (conversation.messages || []).map(mapConversationMessage);
        renderThread();
        renderHistory();
        renderDynamicHints();
    }

    function mapConversationMessage(message) {
        if (message.role === 'assistant') {
            const parsedPayload = tryParseAssistantPayload(message.content);
            if (parsedPayload) {
                return {
                    id: `assistant-${message.id}`,
                    role: 'assistant',
                    data: parsedPayload,
                    timestamp: formatClockTime(message.created_at),
                };
            }
        }

        return {
            id: `${message.role}-${message.id}`,
            role: message.role,
            query: message.content,
            timestamp: formatClockTime(message.created_at),
        };
    }

    function tryParseAssistantPayload(content) {
        try {
            const parsed = JSON.parse(content);
            return parsed && typeof parsed === 'object' ? parsed : null;
        } catch {
            return null;
        }
    }

    function renderDynamicHints() {
        const hintContainer = document.getElementById('aiQueryHints');
        if (!hintContainer) return;

        const lastAssistant = [...messages].reverse().find((message) => message.role === 'assistant' && message.data);
        const suggestions = Array.isArray(lastAssistant?.data?.suggestions) && lastAssistant.data.suggestions.length
            ? lastAssistant.data.suggestions.slice(0, 4)
            : DEFAULT_HINTS;

        hintContainer.innerHTML = `
            <strong>Prompt ideas:</strong>
            ${suggestions.map((suggestion) => `<span class="hint-chip" onclick="AIQueryView.useSuggestion(${JSON.stringify(suggestion).replace(/"/g, '&quot;')})">${escHtml(suggestion)}</span>`).join('')}
        `;
    }

    function toggleDetails(detailId) {
        const detailEl = document.getElementById(detailId);
        if (!detailEl) return;
        detailEl.classList.toggle('is-hidden');
    }

    function persistActiveConversationId(conversationId) {
        if (!conversationId) return;
        window.sessionStorage.setItem(buildStorageKey(), String(conversationId));
    }

    function readStoredConversationId() {
        const raw = window.sessionStorage.getItem(buildStorageKey());
        return raw ? Number(raw) : null;
    }

    function buildStorageKey() {
        return `${STORAGE_KEY_PREFIX}:${currentProgramId || 'none'}:${currentProjectId || 'none'}`;
    }

    function buildConversationTitle(query) {
        const normalized = (query || '').replace(/\s+/g, ' ').trim();
        if (normalized.length <= 72) return normalized;
        return `${normalized.slice(0, 69)}...`;
    }

    function formatClockTime(value) {
        if (!value) return new Date().toLocaleTimeString();
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString();
    }

    function formatRelativeTime(value) {
        if (!value) return '';
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
    }

    function bindComposerShortcuts() {
        const input = document.getElementById('aiQueryInput');
        if (!input || input.dataset.bound === 'true') return;
        input.dataset.bound = 'true';
        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                submitQuery();
            }
        });
    }

    function escHtml(str) {
        const div = document.createElement('div');
        div.textContent = str ?? '';
        return div.innerHTML;
    }

    return { render, submitQuery, executeSQL, useHint, useSuggestion, openConversation, toggleDetails };
})();
