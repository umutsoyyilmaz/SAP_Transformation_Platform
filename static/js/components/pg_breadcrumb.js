/* UI-S02-T05 — PGBreadcrumb: Standard breadcrumb component */
const PGBreadcrumb = (() => {
    /**
     * Standard breadcrumb component.
     * Should be rendered at the top of every view.
     *
     * @param {Array<{ label: string, onclick?: string }>} items
     *   Last item is not clickable (current page).
     * @returns {string} HTML
     */
    function html(items) {
        items = items || [];
        if (!items.length) return '';
        const parts = items.map(function (item, i) {
            const isLast = i === items.length - 1;
            const el = isLast
                ? `<span class="pg-breadcrumb__current" aria-current="page">${_esc(item.label)}</span>`
                : `<a class="pg-breadcrumb__link" href="#" onclick="${item.onclick || ''};return false">${_esc(item.label)}</a>`;
            const sep = isLast ? '' : `<span class="pg-breadcrumb__sep" aria-hidden="true">/</span>`;
            return el + sep;
        });
        return `<nav class="pg-breadcrumb" aria-label="Breadcrumb">${parts.join('')}</nav>`;
    }

    function _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    return { html };
})();
