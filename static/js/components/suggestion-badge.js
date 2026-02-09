/**
 * SAP Transformation Platform — Suggestion Badge (Sprint 7)
 *
 * Global suggestion badge in header, pending count + dropdown panel.
 * Uses dedicated .sugg-* classes to avoid conflicts with notification styles.
 */
const SuggestionBadge = (() => {
    let _pollInterval = null;
    const POLL_MS = 60000;  // 60s polling

    /* ── Type label & icon mapping ─────────────────────────────────────── */
    const TYPE_META = {
        fit_gap_classification: { label: 'Fit/Gap',       icon: '🎯', color: '#0070f2' },
        defect_triage:          { label: 'Defect Triage',  icon: '🐛', color: '#e76500' },
        risk_assessment:        { label: 'Risk',           icon: '⚠️', color: '#cc1919' },
        requirement_analysis:   { label: 'Requirement',    icon: '📋', color: '#30914c' },
    };

    function _typeMeta(type) {
        return TYPE_META[type] || { label: type, icon: '💡', color: '#6a6d70' };
    }

    /* ── Confidence badge color ────────────────────────────────────────── */
    function _confClass(c) {
        if (c >= 0.9) return 'sugg-conf--high';
        if (c >= 0.7) return 'sugg-conf--med';
        return 'sugg-conf--low';
    }

    /* ── Init ──────────────────────────────────────────────────────────── */
    function init() {
        const actionsDiv = document.querySelector('.shell-header__actions');
        if (!actionsDiv) return;

        // Insert suggestion button before notification button
        const firstBtn = actionsDiv.querySelector('button');
        if (firstBtn) {
            firstBtn.insertAdjacentHTML('beforebegin', `
                <button class="shell-header__icon-btn" title="AI Suggestions" style="position:relative"
                        onclick="SuggestionBadge.toggle(event)">💡
                    <span id="suggBadge" class="sugg-badge" style="display:none">0</span>
                </button>
                <div id="suggDropdown" class="sugg-dropdown" style="display:none">
                    <div class="sugg-dropdown__header">
                        <span class="sugg-dropdown__title">💡 AI Suggestions</span>
                        <button class="btn btn-sm" onclick="App.navigate('ai-admin')">View All</button>
                    </div>
                    <div class="sugg-dropdown__body" id="suggList">
                        <p class="sugg-empty">Loading…</p>
                    </div>
                </div>
            `);
        }

        refreshBadge();
        _pollInterval = setInterval(refreshBadge, POLL_MS);
    }

    /* ── Toggle dropdown ───────────────────────────────────────────────── */
    function toggle(e) {
        e?.stopPropagation();
        const dd = document.getElementById('suggDropdown');
        if (!dd) return;
        const visible = dd.style.display !== 'none';
        dd.style.display = visible ? 'none' : 'block';
        if (!visible) loadSuggestions();
    }

    /* ── Refresh badge count ───────────────────────────────────────────── */
    async function refreshBadge() {
        try {
            const data = await API.get('/ai/suggestions/pending-count');
            const badge = document.getElementById('suggBadge');
            if (badge) {
                const count = data.pending_count || 0;
                badge.textContent = count;
                badge.style.display = count > 0 ? 'flex' : 'none';
            }
        } catch { /* AI module may not be active */ }
    }

    /* ── Load suggestion list ──────────────────────────────────────────── */
    async function loadSuggestions() {
        const list = document.getElementById('suggList');
        if (!list) return;
        try {
            const data = await API.get('/ai/suggestions?status=pending&per_page=10');
            if (!data.items || data.items.length === 0) {
                list.innerHTML = '<p class="sugg-empty">No pending suggestions</p>';
                return;
            }
            list.innerHTML = data.items.map(s => {
                const m = _typeMeta(s.suggestion_type);
                const pct = Math.round((s.confidence || 0) * 100);
                const title = s.title || `${m.label} — ${s.entity_type}/${s.entity_id}`;
                return `
                <div class="sugg-item" data-id="${s.id}">
                    <div class="sugg-item__icon" style="background:${m.color}15;color:${m.color}">
                        ${m.icon}
                    </div>
                    <div class="sugg-item__body">
                        <div class="sugg-item__title">${_esc(title)}</div>
                        <div class="sugg-item__meta">
                            <span class="sugg-tag" style="border-color:${m.color};color:${m.color}">${m.label}</span>
                            <span>${_esc(s.entity_type)}/${_esc(String(s.entity_id))}</span>
                            <span class="sugg-conf ${_confClass(s.confidence)}">${pct}%</span>
                        </div>
                    </div>
                    <div class="sugg-item__actions">
                        <button class="sugg-btn sugg-btn--approve" title="Approve"
                                onclick="SuggestionBadge.approve(${s.id}); event.stopPropagation();">✓</button>
                        <button class="sugg-btn sugg-btn--reject" title="Reject"
                                onclick="SuggestionBadge.reject(${s.id}); event.stopPropagation();">✗</button>
                    </div>
                </div>`;
            }).join('');
        } catch {
            list.innerHTML = '<p class="sugg-empty">Could not load suggestions</p>';
        }
    }

    /* ── Approve / Reject ──────────────────────────────────────────────── */
    async function approve(id) {
        try {
            await API.patch(`/ai/suggestions/${id}/approve`, { reviewer: 'user' });
            App.toast('Suggestion approved', 'success');
            refreshBadge();
            loadSuggestions();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    async function reject(id) {
        try {
            await API.patch(`/ai/suggestions/${id}/reject`, { reviewer: 'user' });
            App.toast('Suggestion rejected', 'info');
            refreshBadge();
            loadSuggestions();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    /* ── Helper: basic HTML escape ─────────────────────────────────────── */
    function _esc(str) {
        const el = document.createElement('span');
        el.textContent = str;
        return el.innerHTML;
    }
    /* ── Cleanup ────────────────────────────────────────────────────── */
    function destroy() {
        if (_pollInterval) {
            clearInterval(_pollInterval);
            _pollInterval = null;
        }
    }
    /* ── Close on outside click ────────────────────────────────────────── */
    document.addEventListener('click', (e) => {
        const dd = document.getElementById('suggDropdown');
        if (dd && !dd.contains(e.target) && !e.target.closest('[title="AI Suggestions"]')) {
            dd.style.display = 'none';
        }
    });

    return { init, toggle, refreshBadge, approve, reject, destroy };
})();
