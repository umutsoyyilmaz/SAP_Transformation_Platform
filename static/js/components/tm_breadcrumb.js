/* F1 — TMBreadcrumbBar: Navigation breadcrumb with clickable segments */
var TMBreadcrumbBar = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    /**
     * @param {HTMLElement} container
     * @param {Object}  config
     * @param {Array}   config.items — [{label, onClick?}]  last item is current (no link)
     * @param {string}  [config.separator] — default '/'
     */
    function render(container, config) {
        if (!container) return;
        const { items = [], separator = '/' } = config || {};

        container.innerHTML = `<nav class="tm-breadcrumb">
            ${items.map((item, i) => {
                const isLast = i === items.length - 1;
                const sep = i > 0 ? `<span class="tm-breadcrumb__sep">${esc(separator)}</span>` : '';
                if (isLast) {
                    return `${sep}<span class="tm-breadcrumb__item is-current">${esc(item.label)}</span>`;
                }
                return `${sep}<a class="tm-breadcrumb__item" data-crumb-idx="${i}">${esc(item.label)}</a>`;
            }).join('')}
        </nav>`;

        container.querySelectorAll('[data-crumb-idx]').forEach(link => {
            const idx = Number(link.dataset.crumbIdx);
            const item = items[idx];
            if (item && typeof item.onClick === 'function') {
                link.addEventListener('click', (e) => { e.preventDefault(); item.onClick(); });
            }
        });
    }

    return { render };
})();
