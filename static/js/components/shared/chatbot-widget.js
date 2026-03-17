/**
 * Perga Copilot — Floating Chatbot Widget
 *
 * Self-contained IIFE module. Mounts a floating FAB + chat panel that is
 * accessible from every page in the application.
 *
 * Features:
 *   - SSE streaming via fetch() + ReadableStream (NOT EventSource — POST required)
 *   - Dual mode: general chat (word-by-word stream) + NL query (instant table)
 *   - Conversation persisted in sessionStorage per program
 *   - Auto-creates conversation session on first open
 *   - Graceful fallback on 401 (redirect) and network errors
 *
 * Dependencies (expected as globals):
 *   Auth   — Auth.getAccessToken()
 *   App    — App.getActiveProgram(), App.getActiveProject()  (optional)
 *   API    — API.post(), API.get()
 */
const ChatbotWidget = (() => {
    'use strict';

    // ── State ────────────────────────────────────────────────────────────

    let _convId = null;          // active conversation ID
    let _programId = null;       // active program ID (read from App on open)
    let _isOpen = false;
    let _isStreaming = false;
    let _abortCtrl = null;       // AbortController for in-flight stream
    let _mounted = false;

    // DOM refs — populated in mount()
    let _fab, _panel, _thread, _input, _sendBtn, _closeBtn;

    // ── Storage helpers ──────────────────────────────────────────────────

    function _storageKey() {
        return `chatbot_conv:${_programId || 'global'}`;
    }

    function _loadStoredConvId() {
        try {
            const raw = sessionStorage.getItem(_storageKey());
            return raw ? JSON.parse(raw).id : null;
        } catch (_) {
            return null;
        }
    }

    function _saveConvId(id) {
        try {
            sessionStorage.setItem(_storageKey(), JSON.stringify({ id }));
        } catch (_) { /* storage unavailable */ }
    }

    function _clearStoredConvId() {
        try {
            sessionStorage.removeItem(_storageKey());
        } catch (_) { /* noop */ }
    }

    // ── Auth / program context ───────────────────────────────────────────

    function _getToken() {
        try { return (typeof Auth !== 'undefined') ? Auth.getAccessToken() : null; }
        catch (_) { return null; }
    }

    function _resolveProgramId() {
        try {
            if (typeof App !== 'undefined' && App.getActiveProgram) {
                const prog = App.getActiveProgram();
                return prog ? (prog.id || prog) : null;
            }
        } catch (_) { /* noop */ }
        return null;
    }

    // ── API calls ────────────────────────────────────────────────────────

    async function _ensureConversation() {
        if (_convId) return true;

        _convId = _loadStoredConvId();
        if (_convId) return true;

        try {
            const token = _getToken();
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch('/api/v1/ai/conversations', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    assistant_type: 'general',
                    title: 'Perga Copilot',
                    program_id: _programId,
                }),
            });

            if (res.status === 401) { window.location.href = '/login'; return false; }
            if (!res.ok) { _showSystemMessage('Could not start conversation. Please retry.'); return false; }

            const data = await res.json();
            _convId = data.id;
            _saveConvId(_convId);
            return true;
        } catch (err) {
            _showSystemMessage('Network error. Check your connection.');
            return false;
        }
    }

    async function _loadHistory() {
        if (!_convId) return;
        try {
            const token = _getToken();
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch(`/api/v1/ai/conversations/${_convId}?messages=true`, { headers });
            if (res.status === 404) {
                // Stale conversation — reset
                _clearStoredConvId();
                _convId = null;
                return;
            }
            if (!res.ok) return;

            const data = await res.json();
            const messages = data.messages || [];
            for (const m of messages) {
                if (m.role === 'system') continue;
                _renderPersistedMessage(m);
            }
        } catch (_) { /* silently ignore history load failure */ }
    }

    // ── Open / Close ─────────────────────────────────────────────────────

    async function _open() {
        if (_isOpen) return;
        _isOpen = true;
        _programId = _resolveProgramId();
        _panel.classList.remove('chatbot-panel--closed');
        _input.focus();

        // Clear thread before loading — prevents duplicate history on re-open
        if (_thread.children.length === 0) {
            const ok = await _ensureConversation();
            if (ok && _convId) await _loadHistory();
        }
    }

    function _close() {
        if (!_isOpen) return;
        _isOpen = false;
        _panel.classList.add('chatbot-panel--closed');
        if (_abortCtrl) { _abortCtrl.abort(); _abortCtrl = null; }
        _isStreaming = false;
        _setSendState(false);
    }

    async function _startNewChat() {
        if (_isStreaming) return;
        // Close old conversation
        if (_convId) {
            try {
                const token = _getToken();
                const headers = { 'Content-Type': 'application/json' };
                if (token) headers['Authorization'] = `Bearer ${token}`;
                await fetch(`/api/v1/ai/conversations/${_convId}/close`, { method: 'POST', headers });
            } catch (_) { /* ignore */ }
        }
        _clearStoredConvId();
        _convId = null;
        _thread.innerHTML = '';
        await _ensureConversation();
        _input.focus();
    }

    // ── Send message ─────────────────────────────────────────────────────

    async function _send() {
        const text = _input.value.trim();
        if (!text || _isStreaming) return;

        _input.value = '';
        _input.style.height = '';

        const ok = await _ensureConversation();
        if (!ok) return;

        _isStreaming = true;
        _nlResultRendered = false;
        _setSendState(true);

        // Optimistic user bubble
        _appendBubble('user', text);

        // Skeleton assistant bubble
        const bubbleId = `cb-stream-${Date.now()}`;
        _appendStreamingBubble(bubbleId);
        _scrollToBottom();

        let accum = '';

        try {
            const token = _getToken();
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            _abortCtrl = new AbortController();

            const res = await fetch('/api/v1/ai/chat/stream', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    conversation_id: _convId,
                    message: text,
                    program_id: _programId,
                }),
                signal: _abortCtrl.signal,
            });

            if (res.status === 401) { window.location.href = '/login'; return; }

            if (!res.ok) {
                let errMsg = `Error ${res.status}`;
                try { const d = await res.json(); errMsg = d.error || errMsg; } catch (_) {}
                _finalizeError(bubbleId, errMsg);
                return;
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // keep incomplete line

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    let event;
                    try { event = JSON.parse(line.slice(6)); } catch (_) { continue; }
                    _handleStreamEvent(event, bubbleId, accum, (a) => { accum = a; });
                }
            }

        } catch (err) {
            if (err.name !== 'AbortError') {
                _finalizeError(bubbleId, 'Connection lost. Please retry.');
            } else {
                _finalizeText(bubbleId, accum || '(cancelled)');
            }
        } finally {
            _isStreaming = false;
            _abortCtrl = null;
            _setSendState(false);

            // Safety: if bubble is still in loading state, finalize it
            const wrap = document.getElementById(bubbleId);
            if (wrap) {
                const bubble = wrap.querySelector('.chatbot-msg__bubble--loading');
                if (bubble) {
                    // Bubble never received any content — show fallback
                    if (_nlResultRendered) {
                        // NL result was rendered but done event didn't fire — already visible
                    } else if (accum) {
                        _finalizeText(bubbleId, accum);
                    } else {
                        _finalizeError(bubbleId, 'No response received. Please try again.');
                    }
                }
            }
        }
    }

    // ── Stream event handler ─────────────────────────────────────────────

    let _nlResultRendered = false;

    function _handleStreamEvent(event, bubbleId, accum, setAccum) {
        if (event.type === 'chunk') {
            const newAccum = accum + event.content;
            setAccum(newAccum);
            _updateStreamBubble(bubbleId, newAccum);
        } else if (event.type === 'nl_result') {
            _nlResultRendered = true;
            _finalizeNLResult(bubbleId, event.data);
        } else if (event.type === 'done') {
            // Skip text finalization if NL result already rendered the bubble
            if (!_nlResultRendered) {
                _finalizeText(bubbleId, accum);
            }
        } else if (event.type === 'error') {
            _finalizeError(bubbleId, event.message || 'An error occurred.');
        }
        // "intent" event is ignored in the UI (internal routing hint)
    }

    // ── DOM helpers ──────────────────────────────────────────────────────

    function _appendBubble(role, text) {
        const wrap = document.createElement('div');
        wrap.className = `chatbot-msg chatbot-msg--${role}`;

        const meta = document.createElement('div');
        meta.className = 'chatbot-msg__meta';
        meta.textContent = role === 'user' ? 'You' : 'Perga Copilot';

        const bubble = document.createElement('div');
        bubble.className = 'chatbot-msg__bubble';
        bubble.textContent = text;

        wrap.appendChild(meta);
        wrap.appendChild(bubble);
        _thread.appendChild(wrap);
        _scrollToBottom();
        return { wrap, bubble };
    }

    function _appendStreamingBubble(id) {
        const wrap = document.createElement('div');
        wrap.className = 'chatbot-msg chatbot-msg--assistant';
        wrap.id = id;

        const meta = document.createElement('div');
        meta.className = 'chatbot-msg__meta';
        meta.textContent = 'Perga Copilot';

        const bubble = document.createElement('div');
        bubble.className = 'chatbot-msg__bubble chatbot-msg__bubble--loading';

        const dots = document.createElement('span');
        dots.className = 'chatbot-loading-dots';
        dots.innerHTML = '<span></span><span></span><span></span>';

        bubble.appendChild(dots);
        wrap.appendChild(meta);
        wrap.appendChild(bubble);
        _thread.appendChild(wrap);
        _scrollToBottom();
    }

    function _updateStreamBubble(id, text) {
        const wrap = document.getElementById(id);
        if (!wrap) return;
        const bubble = wrap.querySelector('.chatbot-msg__bubble');
        if (!bubble) return;
        bubble.className = 'chatbot-msg__bubble chatbot-streaming-cursor';
        bubble.textContent = text;
        _scrollToBottom();
    }

    function _finalizeText(id, text) {
        const wrap = document.getElementById(id);
        if (!wrap) return;
        const bubble = wrap.querySelector('.chatbot-msg__bubble');
        if (!bubble) return;
        bubble.className = 'chatbot-msg__bubble';
        bubble.innerHTML = _simpleMarkdown(text || '(no response)');
        _scrollToBottom();
    }

    function _finalizeError(id, message) {
        const wrap = document.getElementById(id);
        if (!wrap) return;
        const bubble = wrap.querySelector('.chatbot-msg__bubble');
        if (!bubble) return;
        bubble.className = 'chatbot-msg__bubble chatbot-msg__bubble--error';
        bubble.textContent = message;
        _scrollToBottom();
    }

    function _finalizeNLResult(id, data) {
        const wrap = document.getElementById(id);
        if (!wrap) return;
        const bubble = wrap.querySelector('.chatbot-msg__bubble');
        if (!bubble) return;
        bubble.className = 'chatbot-msg__bubble';
        bubble.innerHTML = '';

        const container = document.createElement('div');
        container.className = 'chatbot-nl-result';

        // Answer summary text
        if (data.answer) {
            const answer = document.createElement('div');
            answer.className = 'chatbot-nl-answer';
            answer.innerHTML = _simpleMarkdown(data.answer);
            container.appendChild(answer);
        }

        // Results table
        const columns = data.columns || [];
        const rows = data.results || [];

        if (columns.length > 0 && rows.length > 0) {
            const tableWrap = document.createElement('div');
            tableWrap.className = 'chatbot-nl-table-wrap';

            const table = document.createElement('table');
            table.className = 'chatbot-nl-table';

            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            for (const col of columns) {
                const th = document.createElement('th');
                th.textContent = col;
                headerRow.appendChild(th);
            }
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            for (const row of rows) {
                const tr = document.createElement('tr');
                for (const col of columns) {
                    const td = document.createElement('td');
                    const val = Array.isArray(row) ? row[columns.indexOf(col)] : row[col];
                    td.textContent = val === null || val === undefined ? '' : String(val);
                    tr.appendChild(td);
                }
                tbody.appendChild(tr);
            }
            table.appendChild(tbody);
            tableWrap.appendChild(table);
            container.appendChild(tableWrap);

            const rowCount = document.createElement('div');
            rowCount.className = 'chatbot-nl-rowcount';
            rowCount.textContent = `${rows.length} row${rows.length !== 1 ? 's' : ''}`;
            container.appendChild(rowCount);
        } else if (!data.answer) {
            const noData = document.createElement('div');
            noData.className = 'chatbot-nl-answer';
            noData.textContent = 'No results found.';
            container.appendChild(noData);
        }

        bubble.appendChild(container);
        _scrollToBottom();
    }

    function _renderPersistedMessage(msg) {
        if (msg.role === 'assistant') {
            // Try to detect if stored content is an NL result (JSON)
            let parsed = null;
            if (msg.content && msg.content.trim().startsWith('{')) {
                try { parsed = JSON.parse(msg.content); } catch (_) {}
            }
            if (parsed && (parsed.columns || parsed.results || parsed.answer)) {
                const id = `cb-hist-${msg.id || Date.now()}`;
                _appendStreamingBubble(id);
                _finalizeNLResult(id, parsed);
            } else {
                const { bubble } = _appendBubble('assistant', '');
                bubble.innerHTML = _simpleMarkdown(msg.content || '');
            }
        } else {
            _appendBubble('user', msg.content || '');
        }
    }

    function _showSystemMessage(text) {
        const el = document.createElement('div');
        el.style.cssText = 'text-align:center;font-size:12px;color:#999;padding:8px;';
        el.textContent = text;
        _thread.appendChild(el);
    }

    function _scrollToBottom() {
        _thread.scrollTop = _thread.scrollHeight;
    }

    function _setSendState(busy) {
        _sendBtn.disabled = busy;
        _input.disabled = busy;
        _sendBtn.textContent = busy ? '…' : 'Send';
    }

    // ── Simple markdown renderer (bold + inline code + newlines) ─────────

    function _simpleMarkdown(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/`([^`]+)`/g, '<code style="background:#f0f0f0;padding:1px 4px;border-radius:3px;font-size:12px;">$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    // ── HTML structure ───────────────────────────────────────────────────

    function _buildHTML(root) {
        root.innerHTML = `
<button id="chatbot-fab" class="chatbot-fab" title="Perga Copilot" aria-label="Open Perga Copilot">
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
</button>

<div id="chatbot-panel" class="chatbot-panel chatbot-panel--closed" role="dialog" aria-label="Perga Copilot">
  <div class="chatbot-panel__header">
    <span class="chatbot-panel__title">
      <span class="chatbot-panel__title-dot" aria-hidden="true"></span>
      Perga Copilot
    </span>
    <span style="display:flex;gap:4px;align-items:center;">
      <button id="chatbot-new" class="chatbot-panel__close" title="New Chat" aria-label="New Chat" style="font-size:13px;">⟳</button>
      <button id="chatbot-close" class="chatbot-panel__close" title="Close" aria-label="Close Copilot">✕</button>
    </span>
  </div>
  <div id="chatbot-thread" class="chatbot-panel__thread" role="log" aria-live="polite"></div>
  <div class="chatbot-panel__composer">
    <textarea
      id="chatbot-input"
      class="chatbot-panel__input"
      rows="2"
      maxlength="4000"
      placeholder="Ask anything about your SAP project…"
      aria-label="Your message"
    ></textarea>
    <button id="chatbot-send" class="chatbot-panel__send">Send</button>
  </div>
</div>`;
    }

    // ── Public API: mount ────────────────────────────────────────────────

    function mount(rootEl) {
        if (_mounted || !rootEl) return;
        _mounted = true;

        _buildHTML(rootEl);

        _fab      = document.getElementById('chatbot-fab');
        _panel    = document.getElementById('chatbot-panel');
        _thread   = document.getElementById('chatbot-thread');
        _input    = document.getElementById('chatbot-input');
        _sendBtn  = document.getElementById('chatbot-send');
        _closeBtn = document.getElementById('chatbot-close');

        const _newBtn = document.getElementById('chatbot-new');

        // Events
        _fab.addEventListener('click', _open);
        _closeBtn.addEventListener('click', _close);
        _sendBtn.addEventListener('click', _send);
        _newBtn.addEventListener('click', _startNewChat);

        _input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                _send();
            }
        });

        // Auto-resize textarea (up to 5 rows)
        _input.addEventListener('input', () => {
            _input.style.height = 'auto';
            const maxH = parseInt(getComputedStyle(_input).lineHeight || '18', 10) * 5;
            _input.style.height = Math.min(_input.scrollHeight, maxH) + 'px';
        });

        // Close when clicking backdrop (outside panel on mobile)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && _isOpen) _close();
        });
    }

    return { mount };
})();

// Auto-mount after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('chatbot-root');
    if (root) ChatbotWidget.mount(root);
});
