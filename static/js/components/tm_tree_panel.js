var TMTreePanel = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    function render(container, options) {
        if (!container) return;
        const {
            title = 'Groups',
            nodes = [],
            selectedId = 'all',
            searchPlaceholder = 'Filter…',
            onSelect = null,
        } = options || {};

        container.innerHTML = `
            <div class="tm-tree">
                <div class="tm-tree__header">${esc(title)}</div>
                <input class="tm-input tm-tree__search" id="tmTreeSearch" placeholder="${esc(searchPlaceholder)}" />
                <ul class="tm-tree__list" id="tmTreeList"></ul>
            </div>
        `;

        const listEl = container.querySelector('#tmTreeList');
        const searchEl = container.querySelector('#tmTreeSearch');

        const draw = (query = '') => {
            const q = (query || '').trim().toLowerCase();
            const filtered = nodes.filter(n => !q || (n.label || '').toLowerCase().includes(q));
            listEl.innerHTML = filtered.map(n => `
                <li class="tm-tree__item ${String(n.id) === String(selectedId) ? 'is-active' : ''}" data-node-id="${esc(String(n.id))}">
                    <span>${esc(n.label || '')}</span>
                    <span class="tm-tree__count">${n.count ?? ''}</span>
                </li>
            `).join('');

            if (typeof onSelect === 'function') {
                listEl.querySelectorAll('.tm-tree__item').forEach(item => {
                    item.addEventListener('click', () => onSelect(item.dataset.nodeId));
                });
            }
        };

        draw();
        if (searchEl) searchEl.addEventListener('input', (e) => draw(e.target.value));
    }

    return { render };
})();
