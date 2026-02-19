/* F1 — TMContextMenu: Right-click context menu with keyboard shortcuts */
var TMContextMenu = (() => {
    let _menuEl = null;

    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    function _ensureContainer() {
        if (_menuEl) return;
        _menuEl = document.createElement('div');
        _menuEl.className = 'tm-context-menu';
        _menuEl.style.display = 'none';
        document.body.appendChild(_menuEl);

        document.addEventListener('click', () => hide(), true);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') hide();
        });
    }

    /**
     * Show context menu at position.
     * @param {number} x — clientX
     * @param {number} y — clientY
     * @param {Array}  items — [{id, label, shortcut?, icon?, disabled?, divider?, onClick}]
     */
    function show(x, y, items) {
        _ensureContainer();

        _menuEl.innerHTML = items.map(item => {
            if (item.divider) return '<div class="tm-context-menu__divider"></div>';
            const dis = item.disabled ? 'is-disabled' : '';
            return `<div class="tm-context-menu__item ${dis}" data-menu-id="${esc(item.id)}">
                ${item.icon ? `<span class="tm-context-menu__icon">${item.icon}</span>` : '<span class="tm-context-menu__icon"></span>'}
                <span class="tm-context-menu__label">${esc(item.label)}</span>
                ${item.shortcut ? `<span class="tm-context-menu__shortcut">${esc(item.shortcut)}</span>` : ''}
            </div>`;
        }).join('');

        // Position with viewport awareness
        _menuEl.style.display = 'block';
        const rect = _menuEl.getBoundingClientRect();
        const maxX = window.innerWidth - rect.width - 8;
        const maxY = window.innerHeight - rect.height - 8;
        _menuEl.style.left = `${Math.min(x, maxX)}px`;
        _menuEl.style.top = `${Math.min(y, maxY)}px`;

        // Bind clicks
        _menuEl.querySelectorAll('.tm-context-menu__item:not(.is-disabled)').forEach(el => {
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                const item = items.find(i => i.id === el.dataset.menuId);
                if (item && typeof item.onClick === 'function') item.onClick();
                hide();
            });
        });
    }

    function hide() {
        if (_menuEl) _menuEl.style.display = 'none';
    }

    /**
     * Bind a context menu to an element.
     * @param {HTMLElement} element
     * @param {Function} itemsProvider — () => items array
     */
    function bind(element, itemsProvider) {
        if (!element) return;
        element.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            const items = typeof itemsProvider === 'function' ? itemsProvider() : itemsProvider;
            show(e.clientX, e.clientY, items);
        });
    }

    return { show, hide, bind };
})();
