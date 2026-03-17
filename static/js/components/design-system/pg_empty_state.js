/* UI-S02-T03 — PGEmptyState: Standard empty state UI */
const PGEmptyState = (() => {
    /**
     * Standard empty state UI component.
     * Icon + title + description + optional CTA button.
     *
     * @param {Object} opts
     * @param {string} [opts.icon='programs'] — PGIcon key
     * @param {string} opts.title — Title (required)
     * @param {string} [opts.description] — Description text
     * @param {{ label: string, onclick: string }} [opts.action] — CTA button
     * @returns {string} HTML string
     */
    function html(opts) {
        opts = opts || {};
        const icon = opts.icon || 'programs';
        const title = opts.title || 'No items found';
        const description = opts.description || '';
        const action = opts.action || null;

        const iconHtml = (typeof PGIcon !== 'undefined')
            ? `<div class="pg-empty-state__icon">${PGIcon.html(icon, 48)}</div>`
            : '';
        const actionHtml = action
            ? `<button class="pg-btn pg-btn--primary" onclick="${action.onclick}">${_esc(action.label)}</button>`
            : '';
        return `
            <div class="pg-empty-state" role="status">
                ${iconHtml}
                <h3 class="pg-empty-state__title">${_esc(title)}</h3>
                ${description ? `<p class="pg-empty-state__desc">${_esc(description)}</p>` : ''}
                ${actionHtml}
            </div>
        `;
    }

    function _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    return { html };
})();
