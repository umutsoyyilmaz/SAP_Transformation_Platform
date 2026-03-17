/* UI-S01-T03 — PGButton: Standard button HTML helper */
const PGButton = (() => {
    /**
     * Standard button HTML helper.
     * Used in all views instead of btn-primary / tm-btn.
     *
     * @param {string} label
     * @param {'primary'|'secondary'|'ghost'|'danger'|'icon'} variant
     * @param {{ size?: 'sm'|'md'|'lg', loading?: boolean, disabled?: boolean,
     *           onclick?: string, icon?: string, id?: string }} opts
     * @returns {string} HTML
     */
    function html(label, variant, opts) {
        variant = variant || 'secondary';
        opts = opts || {};
        const cls      = `pg-btn pg-btn--${variant}${opts.size ? ` pg-btn--${opts.size}` : ''}`;
        const disabled = (opts.disabled || opts.loading) ? 'disabled' : '';
        const onclick  = opts.onclick ? `onclick="${_escAttr(opts.onclick)}"` : '';
        const id       = opts.id ? `id="${_escAttr(opts.id)}"` : '';
        const inner    = opts.loading
            ? `<span class="pg-btn__spinner"></span>${label}`
            : (opts.icon ? `${opts.icon} ${label}` : label);
        return `<button class="${cls}" ${disabled} ${onclick} ${id}>${inner}</button>`;
    }

    function _escAttr(str) {
        return String(str ?? '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    return { html };
})();
