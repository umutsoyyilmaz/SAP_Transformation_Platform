/* F1 — TMStatusBadge: Compact pill badges with semantic colors */
var TMStatusBadge = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    const PRESETS = {
        // Test case status
        draft:       { bg: '#e0e3e8', fg: '#41474d' },
        ready:       { bg: '#e8f0fe', fg: '#174ea6' },
        approved:    { bg: '#e6f4ea', fg: '#137333' },
        in_review:   { bg: '#fef7cd', fg: '#7c6900' },
        deprecated:  { bg: '#fce8e6', fg: '#a50e0e' },
        // Execution results
        pass:        { bg: '#e6f4ea', fg: '#137333' },
        fail:        { bg: '#fce8e6', fg: '#a50e0e' },
        blocked:     { bg: '#fef7cd', fg: '#7c6900' },
        not_run:     { bg: '#e0e3e8', fg: '#5f6368' },
        deferred:    { bg: '#f3e8fd', fg: '#4a148c' },
        skipped:     { bg: '#e0e3e8', fg: '#5f6368' },
        // Priorities
        low:         { bg: '#e0e3e8', fg: '#41474d' },
        medium:      { bg: '#e8f0fe', fg: '#174ea6' },
        high:        { bg: '#fef7cd', fg: '#7c6900' },
        critical:    { bg: '#fce8e6', fg: '#a50e0e' },
        // Severity
        s1:          { bg: '#fce8e6', fg: '#a50e0e' },
        s2:          { bg: '#fef7cd', fg: '#7c6900' },
        s3:          { bg: '#e8f0fe', fg: '#174ea6' },
        s4:          { bg: '#e0e3e8', fg: '#41474d' },
        // Generic
        open:        { bg: '#e8f0fe', fg: '#174ea6' },
        closed:      { bg: '#e6f4ea', fg: '#137333' },
        active:      { bg: '#e6f4ea', fg: '#137333' },
        inactive:    { bg: '#e0e3e8', fg: '#5f6368' },
    };

    /**
     * Returns an HTML string for a status badge.
     * @param {string} status
     * @param {Object} [opts] — {size: 'sm'|'md', customBg, customFg}
     * @returns {string} HTML
     */
    function html(status, opts) {
        const key = (status || '').toLowerCase().replace(/[\s-]/g, '_');
        const preset = PRESETS[key] || { bg: '#e0e3e8', fg: '#41474d' };
        const bg = opts?.customBg || preset.bg;
        const fg = opts?.customFg || preset.fg;
        const size = opts?.size === 'md' ? 'tm-badge--md' : '';
        return `<span class="tm-badge ${size}" style="background:${bg};color:${fg}">${esc(status || 'unknown')}</span>`;
    }

    /**
     * Render a badge into a container element.
     */
    function render(container, status, opts) {
        if (container) container.innerHTML = html(status, opts);
    }

    return { html, render, PRESETS };
})();
