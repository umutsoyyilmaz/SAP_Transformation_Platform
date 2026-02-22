/* F1 — TMStatusBadge: UI-S01 — delegates to PGStatusRegistry */
/* @deprecated Direct consumers should migrate to PGStatusRegistry.badge() */
var TMStatusBadge = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    /**
     * Returns an HTML string for a status badge.
     * @param {string} status
     * @param {Object} [opts] — {size: 'sm'|'md', customBg, customFg}
     * @returns {string} HTML
     */
    function html(status, opts) {
        // Delegate to PGStatusRegistry if available
        if (typeof PGStatusRegistry !== 'undefined') {
            const { bg: defBg, fg: defFg } = PGStatusRegistry.colors(status);
            const bg = opts?.customBg || defBg;
            const fg = opts?.customFg || defFg;
            const size = opts?.size === 'md' ? 'font-size:13px;padding:3px 10px' : 'font-size:11px;padding:2px 8px';
            return `<span class="tm-badge" style="${size};display:inline-block;border-radius:4px;font-weight:600;background:${bg};color:${fg};white-space:nowrap">${esc(status || 'unknown')}</span>`;
        }
        // Fallback (PGStatusRegistry not yet loaded)
        return `<span class="tm-badge" style="font-size:11px;padding:2px 8px;display:inline-block;border-radius:4px;font-weight:600;background:#f1f5f9;color:#475569;white-space:nowrap">${esc(status || 'unknown')}</span>`;
    }

    /**
     * Render a badge into a container element.
     */
    function render(container, status, opts) {
        if (container) container.innerHTML = html(status, opts);
    }

    // PRESETS kept for backward compat — actual values now come from PGStatusRegistry.MAP
    const PRESETS = typeof PGStatusRegistry !== 'undefined'
        ? PGStatusRegistry.MAP
        : {};

    return { html, render, PRESETS };
})();
