/* F1 — TMToolbar: Action bar with left/right sections, search, filters */
var TMToolbar = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    /**
     * @param {HTMLElement} container
     * @param {Object}  config
     * @param {Array}   config.leftActions   — [{id, label, icon?, primary?, onClick}]
     * @param {Array}   config.rightActions  — [{id, label, icon?, onClick}]
     * @param {boolean} config.showSearch    — render search input
     * @param {string}  config.searchValue   — current search value
     * @param {string}  config.searchPlaceholder
     * @param {Function} config.onSearch     — (query) => void
     * @param {Array}   config.filters       — [{id, label, options:[{value,text}], value}]
     * @param {Function} config.onFilter     — (filterId, value) => void
     * @param {string}  config.viewMode      — 'grid'|'list' (optional toggle)
     * @param {Function} config.onViewToggle — (mode) => void
     */
    function render(container, config) {
        if (!container) return;
        const {
            leftActions = [],
            rightActions = [],
            showSearch = false,
            searchValue = '',
            searchPlaceholder = 'Search…',
            onSearch = null,
            filters = [],
            onFilter = null,
            viewMode = null,
            onViewToggle = null,
        } = config || {};

        const leftBtns = leftActions.map(a =>
            `<button class="tm-toolbar__btn ${a.primary ? 'tm-toolbar__btn--primary' : ''}" data-action-id="${esc(a.id)}">${a.icon ? `<span class="tm-toolbar__icon">${a.icon}</span>` : ''}${esc(a.label)}</button>`
        ).join('');

        const filterEls = filters.map(f =>
            `<select class="tm-toolbar__filter tm-input" data-filter-id="${esc(f.id)}">
                ${(f.options || []).map(o => `<option value="${esc(o.value)}" ${o.value === f.value ? 'selected' : ''}>${esc(o.text)}</option>`).join('')}
            </select>`
        ).join('');

        const searchEl = showSearch
            ? `<input class="tm-input tm-toolbar__search" value="${esc(searchValue)}" placeholder="${esc(searchPlaceholder)}" />`
            : '';

        const viewToggleEl = viewMode
            ? `<div class="tm-toolbar__view-toggle">
                <button class="tm-toolbar__view-btn ${viewMode === 'grid' ? 'is-active' : ''}" data-view="grid" title="Grid View">⊞</button>
                <button class="tm-toolbar__view-btn ${viewMode === 'list' ? 'is-active' : ''}" data-view="list" title="List View">≡</button>
              </div>`
            : '';

        const rightBtns = rightActions.map(a =>
            `<button class="tm-toolbar__btn" data-action-id="${esc(a.id)}">${a.icon ? `<span class="tm-toolbar__icon">${a.icon}</span>` : ''}${esc(a.label)}</button>`
        ).join('');

        container.innerHTML = `
            <div class="tm-toolbar">
                <div class="tm-toolbar__left">
                    ${leftBtns}${filterEls}
                </div>
                <div class="tm-toolbar__right">
                    ${searchEl}${viewToggleEl}${rightBtns}
                </div>
            </div>
        `;

        // Bind actions
        container.querySelectorAll('.tm-toolbar__btn[data-action-id]').forEach(btn => {
            const action = [...leftActions, ...rightActions].find(a => a.id === btn.dataset.actionId);
            if (action && typeof action.onClick === 'function') {
                btn.addEventListener('click', () => action.onClick());
            }
        });

        // Bind search
        if (onSearch) {
            const inp = container.querySelector('.tm-toolbar__search');
            if (inp) inp.addEventListener('input', (e) => onSearch(e.target.value));
        }

        // Bind filters
        if (onFilter) {
            container.querySelectorAll('.tm-toolbar__filter[data-filter-id]').forEach(sel => {
                sel.addEventListener('change', () => onFilter(sel.dataset.filterId, sel.value));
            });
        }

        // Bind view toggle
        if (onViewToggle) {
            container.querySelectorAll('.tm-toolbar__view-btn[data-view]').forEach(btn => {
                btn.addEventListener('click', () => onViewToggle(btn.dataset.view));
            });
        }
    }

    return { render };
})();
